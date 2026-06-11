import streamlit as st
from snowflake.snowpark.context import get_active_session

st.title("🇧🇷🛍️ OLIST : Cohort Analytics")

@st.cache_data( ttl=600, max_entries=5, show_spinner="Now Loading...")
def get_data():
    session = get_active_session()
    session.sql('USE SCHEMA KAGGLE_OLIST_DEV.DBT_DEV').collect()
    fact_df = session.sql('SELECT * FROM FCT_CUSTOMER_COHORT_RETENTION_FULL').to_pandas()
    return fact_df

@st.cache_data(ttl = 600)
def filter_data(col, val, df):
    filtered_df = df[df[col] == val]
    return filtered_df 
fact_df = get_data()
try: 
    filter_cols = [
     'FIRST_PURCHASE_MONTH',
     'LAST_PURCHASE_MONTH',
     'TOTAL_ORDERS',
     'CUSTOMER_CITY',
     'CUSTOMER_STATE',
     'FIRST_PAYMENT_TYPE',
     'CUSTOMER_STATUS']

    with st.sidebar:
       
        st_filter_col = st.selectbox("Chose the dimension of filter", filter_cols)
        filter_vals = ["ALL"] + sorted(fact_df[st_filter_col].unique())
        st_filter_val = st.selectbox("VALUE :", filter_vals)

    if st_filter_val == 'ALL':
        filtered_df = fact_df 
    else: 
        filtered_df = filter_data(st_filter_col, st_filter_val, fact_df)
    
    st.dataframe(filtered_df, use_container_width = True)
    
except Exception as e:
    st.error(f"Error : {e}")


