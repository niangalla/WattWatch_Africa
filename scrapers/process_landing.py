"""Parse les PDF de la landing zone et publie les CSV tidy dans processed/.

Deux modes, choisis par l'environnement (mêmes variables que le spider) :
  - WATTWATCH_S3_BUCKET défini : lit s3://<bucket>/landing/crse/full/, écrit
    s3://<bucket>/processed/. AWS_ENDPOINT_URL permet de pointer MinIO en local.
  - sinon : lit data/landing/crse/full/, écrit data/processed/.

L'utility de chaque grille est déduite du manifest du spider quand il est
disponible (data/landing/crse/manifest.json), sinon SENELEC par défaut.

Usage (tâche Airflow ou CLI) :
    python -m scrapers.process_landing
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

from scrapers.pdf_parser import TARIFF_FIELDS, TRANCHE_FIELDS, parse_grille, write_csv

LANDING_PREFIX = "landing/crse/full/"
PROCESSED_PREFIX = "processed/"
LOCAL_LANDING = Path("data/landing/crse/full")
LOCAL_PROCESSED = Path("data/processed")
MANIFEST = Path("data/landing/crse/manifest.json")

# Concessionnaires d'électrification rurale des grilles harmonisées
CONCESSIONS = ("DPSL", "ERA", "LLK", "SCL")


def utility_map_from_manifest(manifest_path=MANIFEST):
    """{nom de fichier landing -> utility} d'après le manifest du spider."""
    if not manifest_path.exists():
        return {}
    mapping = {}
    docs = json.loads(manifest_path.read_text(encoding="utf-8"))
    for doc in docs:
        slug = doc.get("slug", "")
        utility = "SENELEC"
        for code in CONCESSIONS:
            if re.search(rf"\b{code.lower()}\b", slug):
                utility = code
                break
        for f in doc.get("files", []):
            mapping[Path(f["path"]).name] = utility
    return mapping


def parse_one(pdf_path, utility, out_dir):
    """Parse un PDF → deux CSV dans out_dir. Retourne (n_tarifs, n_tranches)."""
    tariffs, tranches = parse_grille(pdf_path, country_code="SN", utility=utility)
    stem = Path(pdf_path).stem
    write_csv(tariffs, TARIFF_FIELDS, Path(out_dir) / f"{stem}_tarifs.csv")
    write_csv(tranches, TRANCHE_FIELDS, Path(out_dir) / f"{stem}_tranches.csv")
    return len(tariffs), len(tranches)


def process_local(utilities):
    results = []
    for pdf in sorted(LOCAL_LANDING.iterdir()):
        if pdf.is_file():
            utility = utilities.get(pdf.name, "SENELEC")
            results.append((pdf.name, utility, parse_one(pdf, utility, LOCAL_PROCESSED)))
    return results


def process_s3(bucket, utilities):
    import boto3

    s3 = boto3.client("s3", endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=LANDING_PREFIX):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                name = Path(key).name
                local_pdf = tmp / name
                s3.download_file(bucket, key, str(local_pdf))
                utility = utilities.get(name, "SENELEC")
                counts = parse_one(local_pdf, utility, tmp)
                for suffix in ("_tarifs.csv", "_tranches.csv"):
                    csv_name = f"{local_pdf.stem}{suffix}"
                    s3.upload_file(str(tmp / csv_name), bucket, PROCESSED_PREFIX + csv_name)
                results.append((name, utility, counts))
    return results


def main():
    utilities = utility_map_from_manifest()
    bucket = os.getenv("WATTWATCH_S3_BUCKET")
    ok, failed = [], []

    targets = process_s3 if bucket else process_local
    where = f"s3://{bucket}" if bucket else str(LOCAL_LANDING)

    try:
        results = targets(bucket, utilities) if bucket else targets(utilities)
    except FileNotFoundError:
        print(f"Landing zone vide ou absente : {where}")
        return 1

    for name, utility, (n_tarifs, n_tranches) in results:
        line = f"  {name} [{utility}] : {n_tarifs} tarifs, {n_tranches} tranches"
        (ok if n_tarifs else failed).append(line)

    print(f"Landing {where} : {len(ok)} grille(s) parsée(s), {len(failed)} sans tarifs")
    for line in ok + failed:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
