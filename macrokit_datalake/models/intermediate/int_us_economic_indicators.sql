{{
  config(
    materialized='ephemeral'
  )
}}

with staged_data as (
  select * from {{ ref('stg_us_economic_indicators') }}
),

-- Add business logic and enrichments
enriched as (
  select
    series_id,
    observation_date,
    value,
    realtime_start,
    realtime_end,
    country,
    indicator,
    unit,
    frequency,
    source,
    _loaded_at,
    -- Add flag for most current observation per series
    case 
      when realtime_end = '9999-12-31' then true 
      else false 
    end as is_current
  from staged_data
)

select * from enriched