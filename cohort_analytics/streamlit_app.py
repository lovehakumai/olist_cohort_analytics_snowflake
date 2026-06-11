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
def filter_data(col, val, df, dim):
    # 指定されたdim x MONTH_AFTER_FST_PURCHASE での人数をUCNT
    if val == 'ALL':
        filtered_df = df 
    else:
        filtered_df = df[df[col] == val]

    filtered_df = filtered_df[filtered_df["MONTHLY_ORDERS"] > 0]
    filtered_df = filtered_df[filtered_df["MONTHS_AFTER_FST_PURCHASE"] != 0]
    filtered_df = filtered_df.groupby(["MONTHS_AFTER_FST_PURCHASE", dim])[["CUSTOMER_UNIQUE_ID"]].nunique().reset_index()
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

    if "is_executed" not in st.session_state:
        st.session_state.is_executed = False
    if "filter_col" not in st.session_state:
        st.session_state.filter_col = None
    if "filter_val" not in st.session_state:
        st.session_state.filter_val = None

    # formを作るとsubmitボタンを幼い限りコードがrerunしない => fillter_valsが更新されない, なのでcolumns化
    col1, col2 = st.columns(2)
    with col1: 
        st_filter_col = st.selectbox("Chose the dimension of filter", filter_cols)
        filter_vals = ["ALL"] + sorted(fact_df[st_filter_col].unique())
    with col2: 
        st_filter_val = st.selectbox("VALUE :", filter_vals)
    
    is_executed = st.button("Execute")

    # ボタンクリック後にフィルタの値を保持, executedもTrueにする。 => rerunした後もフィルタ設定内容は保持される
    if is_executed:
        st.session_state.is_executed = True 
        st.session_state.filter_col = st_filter_col
        st.session_state.filter_val = st_filter_val 

    if st.session_state.is_executed:
        st.write("---")
        st.subheader("📈 Interactive Line Chart")

        dimension_col = st.selectbox("Chose Dimension Column for Chart legend", filter_cols, key="chart_dim_selector")
        
        filtered_df = filter_data(
            st.session_state.filter_col, 
            st.session_state.filter_val, 
            fact_df, 
            dimension_col
        )
        
        st.line_chart(
            data = filtered_df
            , x = "MONTHS_AFTER_FST_PURCHASE"
            , y = "CUSTOMER_UNIQUE_ID"
            , color = dimension_col
        )

except Exception as e:
    st.error(f"Error : {e}")


