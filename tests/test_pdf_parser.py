"""Tests du parseur de grilles tarifaires.

La fixture est la vraie grille SENELEC applicable au 1er janvier 2026
(source : crse.sn, document public n°2153).
"""

from datetime import date
from pathlib import Path

import pytest

from scrapers.pdf_parser import clean_number, normalize_label, parse_grille

FIXTURE = Path(__file__).parent / "fixtures" / "grille_senelec_20260101.pdf"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("82,00", 82.0),
        ("111 ,23", 111.23),
        ("2 868 ,39", 2868.39),
        ("3 307,93", 3307.93),
        ("-", None),
        ("", None),
        (None, None),
    ],
)
def test_clean_number(raw, expected):
    assert clean_number(raw) == expected


def test_normalize_label_recolle_les_lettres():
    assert normalize_label("P rofessionnel Grande Puissance (PGP)") == (
        "Professionnel Grande Puissance (PGP)"
    )


@pytest.fixture(scope="module")
def grille():
    tariffs, tranches = parse_grille(FIXTURE)
    return tariffs, tranches


def _find(tariffs, **criteria):
    return [t for t in tariffs if all(t.get(k) == v for k, v in criteria.items())]


def test_date_effective(grille):
    tariffs, _ = grille
    assert tariffs[0]["effective_date"] == date(2026, 1, 1).isoformat()


def test_bt_domestique_petite_puissance(grille):
    tariffs, _ = grille
    rows = _find(tariffs, category_code="DPP", payment_mode="postpaiement", band="tranche_1")
    assert len(rows) == 1
    assert rows[0]["price_fcfa_kwh"] == 82.0
    assert rows[0]["voltage_level"] == "BT"


def test_woyofal_present_sans_tranche_3(grille):
    tariffs, _ = grille
    woyofal = _find(tariffs, payment_mode="prepaiement")
    assert {t["category_code"] for t in woyofal} == {"DPP", "DMP", "PPP", "PMP"}
    # Au prépaiement la 3e tranche est valorisée au tarif de la 2e (NB du PDF)
    assert all(t["price_fcfa_kwh"] is None for t in woyofal if t["band"] == "tranche_3")


def test_grande_puissance_heures_pointe(grille):
    tariffs, _ = grille
    pgp = _find(tariffs, category_code="PGP", band="heures_pointe")
    assert len(pgp) == 1
    assert pgp[0]["price_fcfa_kwh"] == 232.23
    assert pgp[0]["prime_fixe_fcfa_kw_month"] == 2868.39


def test_mt_tarif_longue_utilisation(grille):
    tariffs, _ = grille
    tlu = _find(tariffs, category_code="TLU", band="heures_hors_pointe")
    assert len(tlu) == 1
    assert tlu[0]["price_fcfa_kwh"] == 91.93
    assert tlu[0]["voltage_level"] == "MT"


def test_ht_tarif_general(grille):
    tariffs, _ = grille
    ht = _find(tariffs, voltage_level="HT")
    hors_pointe = [t for t in ht if t["band"] == "heures_hors_pointe"]
    assert 71.43 in [t["price_fcfa_kwh"] for t in hors_pointe]


def test_bornes_tranches(grille):
    _, tranches = grille
    ud_pp = [t for t in tranches if t["option_code"] == "UD-PP"]
    assert len(ud_pp) == 3
    t1 = next(t for t in ud_pp if t["tranche"] == 1)
    assert (t1["kwh_min"], t1["kwh_max"]) == (0, 150)
    t3 = next(t for t in ud_pp if t["tranche"] == 3)
    assert (t3["kwh_min"], t3["kwh_max"]) == (251, None)


def test_volume_global(grille):
    tariffs, tranches = grille
    assert len(tariffs) >= 30  # BT (12 cat.×tranches) + Woyofal + GP + MT/HT
    assert len(tranches) == 12  # 4 options × 3 tranches
