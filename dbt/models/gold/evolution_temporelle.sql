-- Indice d'evolution temporelle (base 100) : prix indexe sur la premiere
-- grille observee, par ligne tarifaire (meme pays/operateur/categorie/mode
-- de paiement/tranche). Un seul point tant qu'une seule grille a ete
-- ingeree ; prend son sens a mesure que l'historique s'accumule.
-- Partitionne sur `category` (toujours renseigne), pas `category_code`
-- (nul pour certaines categories, cf. silver/tarifs_electricite.sql).
select
    country_code,
    utility,
    category,
    category_code,
    payment_mode,
    band,
    effective_date,
    price_fcfa_kwh,
    first_value(price_fcfa_kwh) over (
        partition by country_code, utility, category, payment_mode, band
        order by effective_date
        rows between unbounded preceding and unbounded following
    ) as prix_base,
    100.0 * price_fcfa_kwh / nullif(
        first_value(price_fcfa_kwh) over (
            partition by country_code, utility, category, payment_mode, band
            order by effective_date
            rows between unbounded preceding and unbounded following
        ),
        0
    ) as indice_base_100
from {{ ref('tarifs_electricite') }}
