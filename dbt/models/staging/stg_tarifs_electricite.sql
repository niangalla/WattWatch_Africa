-- Bronze → staging : typage et déduplication des lignes tarifaires
select
    country_code,
    utility,
    cast(effective_date as date) as effective_date,
    voltage_level,
    section,
    category,
    category_code,
    payment_mode,
    band,
    cast(price_fcfa_kwh as number(10, 2)) as price_fcfa_kwh,
    cast(prime_fixe_fcfa_kw_month as number(12, 2)) as prime_fixe_fcfa_kw_month,
    source_file,
    cast(parsed_at as timestamp_ntz) as parsed_at
from {{ source('bronze', 'raw_tarifs_electricite') }}
qualify row_number() over (
    partition by country_code, utility, effective_date, voltage_level,
                 section, category, payment_mode, band
    order by parsed_at desc
) = 1
