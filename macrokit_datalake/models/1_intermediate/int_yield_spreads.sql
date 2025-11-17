{{
  config(
    materialized='ephemeral'
  )
}}

with yields as (
    select * from {{ ref('stg_treasury_yields') }}
),

-- Pivot yields to get all maturities on one row
pivoted as (
    select
        date,
        country,
        max(case when maturity = '2Y' then yield end) as yield_2y,
        max(case when maturity = '5Y' then yield end) as yield_5y,
        max(case when maturity = '10Y' then yield end) as yield_10y,
        max(case when maturity = '30Y' then yield end) as yield_30y
    from yields
    group by date, country
),

-- Calculate spreads
spreads as (
    select
        date,
        country,
        yield_2y,
        yield_5y,
        yield_10y,
        yield_30y,
        
        -- Spreads in basis points
        (yield_10y - yield_2y) * 100 as spread_2s10s,
        (yield_30y - yield_10y) * 100 as spread_10s30s,
        (yield_30y - yield_2y) * 100 as spread_2s30s,
        
        -- Yield curve slope (proxy)
        case 
            when yield_10y > yield_2y then 'NORMAL'
            when yield_10y < yield_2y then 'INVERTED'
            else 'FLAT'
        end as curve_shape
        
    from pivoted
    where yield_2y is not null 
      and yield_10y is not null
)

select * from spreads