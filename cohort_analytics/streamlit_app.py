import streamlit as st
from snowflake.snowpark.context import get_active_session

st.title("🇧🇷🛍️ OLIST : Cohort Analytics")

session = get_active_session()
session.sql('USE SCHEMA KAGGLE_OLIST_DEV.DBT_DEV').collect()
df = session.sql('SELECT * FROM FCT_CUSTOMER_COHORT_RETENTION').to_pandas()
st.markdown("---")
exclude_m0 = st.checkbox("EXCLUDE FIRST MONTH")
if exclude_m0:
    df = df[df['MONTHS_AFTER_FIRST_PURCHASE'] > 0]
st.markdown("---")
st.header("⭐️NUM OF CUSTOMERS")
st.line_chart(
    data=df, 
    x = "MONTHS_AFTER_FIRST_PURCHASE", 
    y = "UCNT_RETAINED",
    color = "FIRST_PURCHASE_MONTH"
)

st.header("⭐️NUM OF ORDERS")
st.line_chart(
    data=df, 
    x = "MONTHS_AFTER_FIRST_PURCHASE", 
    y = "ORDER_CNT_RETAINED",
    color = "FIRST_PURCHASE_MONTH"
)

st.header("⭐️SUM OF AMOUNT")
st.line_chart(
    data=df, 
    x = "MONTHS_AFTER_FIRST_PURCHASE", 
    y = "REVENUE_RETAINED",
    color = "FIRST_PURCHASE_MONTH"
)
