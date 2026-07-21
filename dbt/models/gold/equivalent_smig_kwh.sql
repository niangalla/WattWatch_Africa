-- Equivalent en kWh du SMIG mensuel, par ligne tarifaire.
-- Conversion horaire -> mensuelle : 52 semaines / 12 mois x heures legales
-- hebdomadaires, convention standard du droit du travail senegalais.
-- Explicite ici plutot que figee dans le seed, pour rester auditable.
with smig_mensuel as (
    select
        country_code,
        smig_fcfa_heure,
        heures_semaine_legales,
        smig_fcfa_heure * heures_semaine_legales * 52.0 / 12 as smig_fcfa_mois,
        texte_reference as smig_source
    from {{ ref('ref_smig') }}
)

select
    t.tariff_id,
    t.country_code,
    t.utility,
    t.effective_date,
    t.category,
    t.payment_mode,
    t.band,
    t.price_fcfa_kwh,
    s.smig_fcfa_mois,
    s.smig_source,
    s.smig_fcfa_mois / nullif(t.price_fcfa_kwh, 0) as kwh_equivalent_smig
from {{ ref('cout_unitaire_kwh') }} t
join smig_mensuel s on s.country_code = t.country_code
