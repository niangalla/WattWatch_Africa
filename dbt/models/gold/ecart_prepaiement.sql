-- Ecart prepaiement (Woyofal) vs post-paiement, a categorie et tranche
-- identiques. Woyofal partage les memes libelles de categorie que le
-- post-paiement (memes tranches BT) : seul le payment_mode change entre
-- les deux lignes a comparer.
select
    country_code,
    utility,
    effective_date,
    category,
    category_code,
    band,
    max(case when payment_mode = 'prepaiement' then price_fcfa_kwh end) as prix_prepaiement,
    max(case when payment_mode = 'postpaiement' then price_fcfa_kwh end) as prix_postpaiement,
    max(case when payment_mode = 'prepaiement' then price_fcfa_kwh end)
        - max(case when payment_mode = 'postpaiement' then price_fcfa_kwh end) as ecart_fcfa_kwh
from {{ ref('tarifs_electricite') }}
where voltage_level = 'BT'
group by country_code, utility, effective_date, category, category_code, band
having count(distinct payment_mode) = 2
