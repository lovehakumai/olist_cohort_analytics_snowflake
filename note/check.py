from snowflake.snowpark.context import get_active_session
session = get_active_session()
db = 'KAGGLE_OLIST_DEV'
schema = 'DBT_DEV'
table = ''
session.sql(f'USE SCHEMA {db}.{schema}').collect()

fact_df = session.sql('SELECT * FROM KAGGLE_OLIST_DEV.DBT_DEV.FCT_CUSTOMER_COHORT_RETENTION_FULL').to_pandas()
dim_dif = sessio.sql('SELECT * FROM KAGGLE_OLIST_DEV.DBT_DEV.DIM_CUSTOMER_LIFECYCLE').to_pandas()

fact_df.columns

