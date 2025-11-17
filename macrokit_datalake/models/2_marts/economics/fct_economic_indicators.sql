{{ config(
    materialized='table',
    indexes=[
      {'columns': ['country_code', 'indicator_date'], 'type': 'btree'},
      {'columns': ['indicator_name'], 'type': 'btree'}
    ]
) }}

with economic_data as (
    select
        country_code,
        indicator_name,
        indicator_date,
        indicator_value,
        source_system,
        created_at
    from {{ ref('int_economic_indicators_cleaned') }}
),

latest_values as (
    select
        country_code,
        indicator_name,
        indicator_date,
        indicator_value,
        lag(indicator_value) over (
            partition by country_code, indicator_name 
            order by indicator_date
        ) as previous_value,
        source_system,
        created_at
    from economic_data
)

select
    country_code,
    indicator_name,
    indicator_date,
    indicator_value,
    previous_value,
    case 
        when previous_value is not null and previous_value != 0
        then ((indicator_value - previous_value) / previous_value) * 100
        else null
    end as period_change_pct,
    source_system,
    created_at,
    current_timestamp as dbt_updated_at
from latest_values