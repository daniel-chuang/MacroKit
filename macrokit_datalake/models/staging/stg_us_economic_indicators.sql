{{
  config(
    materialized='view'
  )
}}

with source as (
  select * from {{ source('raw', 'us_economic_indicators') }}
),

-- Clean and standardize the data
cleaned as (
  select
    series_id,
    observation_date,
    value,
    realtime_start,
    realtime_end,
    'US' as country,
    indicator,
    unit,
    frequency,
    source,
    _loaded_at
  from source
  where value is not null
    and observation_date is not null
    and series_id is not null
)

select * from cleaned