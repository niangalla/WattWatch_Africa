-- Staging -> Silver : passage a une table materialisee, contrat stable pour Gold.
-- La cle se base sur `category` (toujours renseigne) et non `category_code`,
-- qui est nul pour les categories sans sigle entre parentheses dans la grille
-- (Tarif Secours, Tarif General, Eclairage Public...).
select
    country_code || '|' || utility || '|' || cast(effective_date as varchar) || '|'
        || category || '|' || payment_mode || '|' || band as tariff_id,
    country_code,
    utility,
    effective_date,
    voltage_level,
    section,
    category,
    category_code,
    payment_mode,
    band,
    price_fcfa_kwh,
    prime_fixe_fcfa_kw_month
from {{ ref('stg_tarifs_electricite') }}
