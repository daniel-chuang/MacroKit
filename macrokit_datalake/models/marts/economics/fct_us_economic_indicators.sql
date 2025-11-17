{{
  config(
    materialized='table'
  )
}}

with intermediate_data as (
  select * from {{ ref('int_us_economic_indicators') }}
),

final as (
  select
    series_id,
    observation_date,
    value,
    realtime_start,
    realtime_end,
    country,
    indicator,
    unit,
    source,
    frequency,
    is_current,
    _loaded_at
  from intermediate_data
)

select * from final