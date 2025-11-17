{{
  config(
    materialized='table'
  )
}}

select * from {{ ref('int_yield_spreads') }}