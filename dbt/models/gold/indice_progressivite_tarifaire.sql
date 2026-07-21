-- Indice de progressivite tarifaire : rapport entre le prix de la derniere
-- tranche et celui de la premiere, pour les grilles BT a tranches
-- progressives (tranche_1/2/3).
select
    country_code,
    utility,
    effective_date,
    category_code,
    category,
    payment_mode,
    max(case when band = 'tranche_1' then price_fcfa_kwh end) as prix_tranche_1,
    max(case when band = 'tranche_3' then price_fcfa_kwh end) as prix_tranche_3,
    max(case when band = 'tranche_3' then price_fcfa_kwh end)
        / nullif(max(case when band = 'tranche_1' then price_fcfa_kwh end), 0)
        as indice_progressivite
from {{ ref('tarifs_electricite') }}
where band in ('tranche_1', 'tranche_2', 'tranche_3')
group by country_code, utility, effective_date, category_code, category, payment_mode
