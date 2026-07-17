"""Parseur des grilles tarifaires CRSE (format SENELEC) — pdfplumber.

Transforme le PDF officiel « Grille tarifaire de Senelec » en enregistrements
*tidy* (une ligne = un prix), prêts pour la landing zone puis le Bronze :

    country_code, utility, effective_date, voltage_level, section, category,
    category_code, payment_mode, band, price_fcfa_kwh, prime_fixe_fcfa_kw_month

Trois tables sont extraites du PDF :
  1. Basse tension (tranches 1/2/3 + Woyofal + Grande Puissance pointe/hors-pointe)
  2. Moyenne/Haute tension (heures pointe/hors-pointe + prime fixe)
  3. Bornes des tranches de consommation (kWh min/max par option tarifaire)

Usage :
    python -m scrapers.pdf_parser <grille.pdf> -o data/processed/
"""

import argparse
import csv
import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

import pdfplumber

FRENCH_MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}

TARIFF_FIELDS = [
    "country_code", "utility", "effective_date", "voltage_level", "section",
    "category", "category_code", "payment_mode", "band", "price_fcfa_kwh",
    "prime_fixe_fcfa_kw_month", "source_file", "parsed_at",
]

TRANCHE_FIELDS = [
    "country_code", "utility", "effective_date", "option_code", "tranche",
    "kwh_min", "kwh_max", "source_file", "parsed_at",
]


def strip_accents(text):
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if not unicodedata.combining(c))


def normalize_label(text):
    """Nettoie un libellé : espaces parasites de l'extraction PDF.

    pdfplumber produit parfois « P rofessionnel » ou « 111 ,23 ».
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    # Lettre isolée recollée au mot suivant (« P rofessionnel » → « Professionnel »)
    text = re.sub(r"\b([A-ZÉÈ]) (?=[a-zé])", r"\1", text)
    return text


def clean_number(raw):
    """« 2 868 ,39 » → 2868.39 ; « - », « » ou None → None."""
    if raw is None:
        return None
    txt = str(raw).replace(" ", " ").strip()
    if txt in ("", "-", "—"):
        return None
    txt = txt.replace(" ", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def _key(text):
    return strip_accents(normalize_label(text or "")).lower()


def _non_empty_cells(row):
    return [c.strip() for c in row if c is not None and str(c).strip() != ""]


def _category_code(label):
    m = re.search(r"\(([A-Z]{2,5})\)", label)
    return m.group(1) if m else None


def parse_effective_date(page_text):
    """« APPLICABLE A COMPTER DU 1er JANVIER 2026 » → date(2026, 1, 1)."""
    text = _key(page_text)
    m = re.search(r"compter\s+du\s+(1er|\d{1,2})\s+([a-z]+)\s+(\d{4})", text)
    if not m:
        return None
    day = 1 if m.group(1) == "1er" else int(m.group(1))
    month = FRENCH_MONTHS.get(m.group(2))
    if not month:
        return None
    return date(int(m.group(3)), month, day)


def _is_section_row(cells):
    return len(cells) == 1 and not any(ch.isdigit() for ch in cells[0])


def _parse_bt_table(table):
    """Table basse tension : sections UD/UP/Woyofal (tranches) et GP (pointe)."""
    records = []
    section = None
    for row in table:
        cells = _non_empty_cells(row)
        if not cells:
            continue
        label = normalize_label(cells[0])
        label_key = _key(label)
        if "categories tarifaires" in label_key or "tranche" in label_key:
            continue  # lignes d'en-tête

        numbers = [clean_number(c) for c in cells[1:]]
        if all(n is None for n in numbers):
            # Aucun prix : c'est un en-tête de section, éventuellement suivi
            # des libellés de bandes (ex. « Usage Grande Puissance | Heures
            # Hors Pointe | Heures de Pointe »)
            section = label
            continue
        section_key = _key(section or "")

        if "grande puissance" in section_key:
            # [hors pointe, pointe, prime fixe]
            bands = list(zip(["heures_hors_pointe", "heures_pointe"], numbers[:2], strict=False))
            prime = numbers[2] if len(numbers) > 2 else None
        elif "eclairage" in _key(label):
            bands = [("unique", numbers[0] if numbers else None)]
            prime = numbers[1] if len(numbers) > 1 else None
        else:
            bands = list(zip(["tranche_1", "tranche_2", "tranche_3"], numbers[:3], strict=False))
            prime = numbers[3] if len(numbers) > 3 else None

        payment = "prepaiement" if "woyofal" in section_key else "postpaiement"
        for band, price in bands:
            if price is None and band != "tranche_3":
                continue
            records.append({
                "voltage_level": "BT",
                "section": section,
                "category": label,
                "category_code": _category_code(label),
                "payment_mode": payment,
                "band": band,
                "price_fcfa_kwh": price,
                "prime_fixe_fcfa_kw_month": prime,
            })
    return records


def _parse_mt_ht_table(table):
    """Table moyenne/haute tension : heures pointe / hors-pointe + prime fixe."""
    records = []
    voltage = None
    for row in table:
        cells = _non_empty_cells(row)
        if not cells:
            continue
        label = normalize_label(cells[0])
        label_key = _key(label)
        if "moyenne tension" in label_key:
            voltage = "MT"
            continue
        if "haute tension" in label_key:
            voltage = "HT"
            continue
        if _is_section_row(cells) or "categorie" in label_key or "prix de" in label_key:
            continue

        numbers = [n for n in (clean_number(c) for c in cells[1:]) if n is not None]
        if not numbers:
            continue
        if len(numbers) >= 3:
            bands = [("heures_hors_pointe", numbers[0]), ("heures_pointe", numbers[1])]
            prime = numbers[2]
        else:
            bands = [("unique", numbers[0])]
            prime = numbers[1] if len(numbers) > 1 else None

        for band, price in bands:
            records.append({
                "voltage_level": voltage,
                "section": f"Livraison en {'Moyenne' if voltage == 'MT' else 'Haute'} Tension",
                "category": label,
                "category_code": _category_code(label),
                "payment_mode": "postpaiement",
                "band": band,
                "price_fcfa_kwh": price,
                "prime_fixe_fcfa_kw_month": prime,
            })
    return records


def _parse_tranche_table(table):
    """Bornes des tranches : « De 0 à 150 kWh », « Plus de 250 kWh »."""
    records = []
    for row in table:
        cells = _non_empty_cells(row)
        if len(cells) < 2 or "option" in _key(cells[0]):
            continue
        option = normalize_label(cells[0])
        tranche_no = 0
        for cell in cells[1:]:
            cell_key = _key(cell)
            bounds = re.findall(r"\d+", cell_key)
            if not bounds or "kwh" not in cell_key:
                continue
            tranche_no += 1
            if "plus de" in cell_key:
                kwh_min, kwh_max = int(bounds[0]) + 1, None
            elif len(bounds) >= 2:
                kwh_min, kwh_max = int(bounds[0]), int(bounds[1])
            else:
                kwh_min, kwh_max = 0, int(bounds[0])
            records.append({
                "option_code": option,
                "tranche": tranche_no,
                "kwh_min": kwh_min,
                "kwh_max": kwh_max,
            })
    return records


def _classify_table(table):
    flat = _key(" ".join(str(c) for row in table for c in row if c))
    if "option tarifaire" in flat:
        return "tranches"
    if "moyenne tension" in flat or "haute tension" in flat:
        return "mt_ht"
    if "categories tarifaires" in flat:
        return "bt"
    return None


def parse_grille(pdf_path, country_code="SN", utility="SENELEC"):
    """Parse une grille tarifaire PDF → (tarifs, bornes de tranches)."""
    pdf_path = Path(pdf_path)
    tariffs, tranches = [], []
    effective_date = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if effective_date is None:
                effective_date = parse_effective_date(page.extract_text() or "")
            for table in page.extract_tables():
                kind = _classify_table(table)
                if kind == "bt":
                    tariffs.extend(_parse_bt_table(table))
                elif kind == "mt_ht":
                    tariffs.extend(_parse_mt_ht_table(table))
                elif kind == "tranches":
                    tranches.extend(_parse_tranche_table(table))

    common = {
        "country_code": country_code,
        "utility": utility,
        "effective_date": effective_date.isoformat() if effective_date else None,
        "source_file": pdf_path.name,
        "parsed_at": datetime.now(UTC).isoformat(),
    }
    for rec in tariffs + tranches:
        rec.update(common)
    return tariffs, tranches


def write_csv(records, fields, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Parse une grille tarifaire CRSE/SENELEC")
    parser.add_argument("pdf", help="chemin du PDF")
    parser.add_argument("-o", "--out-dir", default="data/processed", help="dossier de sortie")
    parser.add_argument("--country", default="SN")
    parser.add_argument("--utility", default="SENELEC")
    args = parser.parse_args(argv)

    tariffs, tranches = parse_grille(args.pdf, args.country, args.utility)
    stem = Path(args.pdf).stem
    out_dir = Path(args.out_dir)
    write_csv(tariffs, TARIFF_FIELDS, out_dir / f"{stem}_tarifs.csv")
    write_csv(tranches, TRANCHE_FIELDS, out_dir / f"{stem}_tranches.csv")
    print(f"{len(tariffs)} lignes tarifaires, {len(tranches)} bornes de tranches -> {out_dir}/")


if __name__ == "__main__":
    main()
