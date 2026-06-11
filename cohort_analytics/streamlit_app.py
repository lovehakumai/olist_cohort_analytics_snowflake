import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

st.set_page_config(layout="wide")

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
        tmp_df = df.copy()
    else:
        tmp_df = df[df[col] == val].copy()
        
    # 全ての合計数字を取得して返す
    customer_total = tmp_df['CUSTOMER_UNIQUE_ID'].nunique()
    revenue_total = tmp_df['MONTHLY_REVENUE'].sum()
    order_total = tmp_df['MONTHLY_ORDERS'].sum()
    major_dict = {"customer": customer_total, "revenue": revenue_total, "order": order_total}

    filtered_df = tmp_df[tmp_df["MONTHLY_ORDERS"] > 0]
    filtered_df = filtered_df[filtered_df["MONTHS_AFTER_FST_PURCHASE"] != 0]
    filtered_df = (

        filtered_df
        .groupby(["MONTHS_AFTER_FST_PURCHASE", dim])
        .agg({
            "CUSTOMER_UNIQUE_ID" : "nunique",
            "MONTHLY_REVENUE": "sum",
            "MONTHLY_ORDERS": "sum"
            })
        .reset_index()
    )
    # 経過月数 x 指定粒度での累積和を算出して、0M時点での人数で割る
    filtered_df = filtered_df.sort_values(by = [dim, 'MONTHS_AFTER_FST_PURCHASE'])
    filtered_df[f'{dim}_cumsum'] = filtered_df.groupby(dim)['MONTHLY_REVENUE'].cumsum()
    denom_df = (
        tmp_df[tmp_df["MONTHS_AFTER_FST_PURCHASE"] == 0]
        .groupby(dim)
        .agg(uu_cus_id = ("CUSTOMER_UNIQUE_ID", "nunique"))
        .reset_index()
    )
    merged_clv_df = pd.merge(filtered_df, denom_df, on = dim, how = 'left')
    merged_clv_df["cus_clv"] = merged_clv_df[f"{dim}_cumsum"] / merged_clv_df["uu_cus_id"]

    result = {
        "filtered_df": filtered_df, 
        "major_dict": major_dict,
        "clv_df": merged_clv_df
    }
    return result

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
        filter_vals = ["ALL"] + sorted(fact_df[st_filter_col].dropna().unique())
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
        dimension_col = st.selectbox(
            "Chose Dimension Column for Chart legend"
            , filter_cols
            , key="chart_dim_selector"
        )
        
        result_dict = filter_data(
            st.session_state.filter_col, 
            st.session_state.filter_val, 
            fact_df, 
            dimension_col
        )

        col1, col2, col3 = st.columns(3)
        with col1: 
            st.metric(label='👦 CUSTOMER',value = f"{result_dict['major_dict']['customer']:,.2f}")
            st.line_chart(
                data = result_dict["filtered_df"]
                , x = "MONTHS_AFTER_FST_PURCHASE"
                , y = "CUSTOMER_UNIQUE_ID"
                , color = dimension_col
            )
        
        with col2: 
            st.metric(label='💰 REVENUE',value = f"{result_dict['major_dict']['revenue']:,.2f}")
            st.line_chart(
                data = result_dict["filtered_df"]
                , x = "MONTHS_AFTER_FST_PURCHASE"
                , y = "MONTHLY_REVENUE"
                , color = dimension_col
            )

        with col3: 
            st.metric(label='🧾 ORDERS',value = f"{result_dict['major_dict']['order']:,.2f}")
            
            st.line_chart(
                data = result_dict["filtered_df"]
                , x = "MONTHS_AFTER_FST_PURCHASE"
                , y = "MONTHLY_ORDERS"
                , color = dimension_col
            )

        st.write('---')
        st.subheader("💰👦Customer Life Value(CLV)")
        st.line_chart(
            data = result_dict["clv_df"]
            , x = "MONTHS_AFTER_FST_PURCHASE"
            , y = "cus_clv"
            , color = dimension_col
        )

except Exception as e:
    st.error(f"Error : {e}")


