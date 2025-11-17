{{
  config(
    materialized='view'
  )
}}

with source as (
  select * from {{ source('raw', 'us_market_data') }}
),

-- Filter to only treasury yields
treasury_yields as (
  select
    date,
    series_id,
    value as yield,
    maturity,
    indicator,
    _loaded_at
  from source
  where asset_class = 'TREASURY'
    and value is not null
),

-- Add any additional transformations or enrichments
transformed as (
  select
    date,
    'US' as country,
    maturity,
    yield,
    series_id,
    indicator,
    _loaded_at
  from treasury_yields
)

select * from transformed