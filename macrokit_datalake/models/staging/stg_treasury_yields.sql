{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'treasury_yields') }}
),

maturity_mapping as (
    select 'DGS1MO' as series_id, '1M' as maturity union all
    select 'DGS3MO', '3M' union all
    select 'DGS6MO', '6M' union all
    select 'DGS1', '1Y' union all
    select 'DGS2', '2Y' union all
    select 'DGS5', '5Y' union all
    select 'DGS10', '10Y' union all
    select 'DGS30', '30Y'
),

transformed as (
    select
        s.date,
        'US' as country,
        m.maturity,
        s.value as yield,
        s._loaded_at
        
    from source s
    inner join maturity_mapping m
        on s.series_id = m.series_id
    
    where s.value is not null
)

select * from transformed