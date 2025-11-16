{{
  config(
    materialized='table'
  )
}}

with staging as (
    select * from {{ ref('stg_treasury_yields') }}
),

final as (
    select
        date,
        country,
        maturity,
        yield
        
    from staging
)

select * from final