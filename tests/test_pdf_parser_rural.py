"""Tests du parseur des grilles harmonisees de concessions rurales.

La fixture est la vraie grille ERA applicable au 1er janvier 2026
(source : crse.sn, document public n°2574). Meme format que LLK, DPSL
et SCL (verifie manuellement lors du developpement, non fixture ici
pour eviter de multiplier des PDF quasi identiques dans le repo).
"""

from pathlib import Path

import pytest

from scrapers.pdf_parser import parse_grille

FIXTURE = Path(__file__).parent / "fixtures" / "grille_era_20260101.pdf"


@pytest.fixture(scope="module")
def grille():
    tariffs, tranches = parse_grille(FIXTURE, utility="ERA")
    return tariffs, tranches


def _find(tariffs, **criteria):
    return [t for t in tariffs if all(t.get(k) == v for k, v in criteria.items())]


def test_date_effective(grille):
    tariffs, _ = grille
    assert tariffs[0]["effective_date"] == "2026-01-01"


def test_volume_global(grille):
    tariffs, tranches = grille
    # 2 categories (Domestique/Professionnel) x 2 sections (Reseau/Kit
    # solaire) x 4 services
    assert len(tariffs) == 16
    assert tranches == []


def test_domestique_reseau(grille):
    tariffs, _ = grille
    rows = _find(tariffs, category="Domestique", section="Reseau")
    assert len(rows) == 4
    assert {r["band"] for r in rows} == {"service_1", "service_2", "service_3", "service_4"}
    assert all(r["price_fcfa_kwh"] == 82.0 for r in rows)


def test_domestique_kit_solaire_service_4_moins_cher(grille):
    tariffs, _ = grille
    rows = _find(tariffs, category="Domestique", section="Kit solaire", band="service_4")
    assert len(rows) == 1
    assert rows[0]["price_fcfa_kwh"] == 40.0


def test_professionnel_plus_cher_que_domestique(grille):
    tariffs, _ = grille
    dom = _find(tariffs, category="Domestique", section="Reseau", band="service_1")[0]
    pro = _find(tariffs, category="Professionnel", section="Reseau", band="service_1")[0]
    assert pro["price_fcfa_kwh"] > dom["price_fcfa_kwh"]


def test_toutes_les_lignes_sont_prepaiement(grille):
    tariffs, _ = grille
    assert {t["payment_mode"] for t in tariffs} == {"prepaiement"}


def test_utility_transmise(grille):
    tariffs, _ = grille
    assert {t["utility"] for t in tariffs} == {"ERA"}
