-- Cout unitaire par kWh et par tranche : exposition directe de Silver,
-- nommage et grain stables pour le serving (Power BI).
select
    tariff_id,
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
from {{ ref('tarifs_electricite') }}
