# stageに保存したzipファイルに含まれるCSVファイルを取得して、指定したテーブルに作成する
# 参考 : https://zenn.dev/0w0/articles/af542054ba81de

import zipfile
import os
import polars as pl
import io  
from pathlib import Path
from snowflake.snowpark.context import get_active_session
from zipfile import ZipFile 

session = get_active_session()
stage_abs_path = '@"KAGGLE_OLIST"."PUBLIC"."KAGGLE_OLIST"/kaggle_olist.zip'

# get_streamでデータを取得する
zipfile_buffer = session.file.get_stream(stage_abs_path, decompress=False)

# ZipFile関数はダックコードでPath, データオブジェクトどちらかを渡すことで挙動が変わる
# Pathを渡した時に挙動するのは、実行環境のディスクにデータがある場合のみ
# この環境はCOMPUTE_POOLで実行されてるので、Stageがあるのは別のディスクだからデータオブジェクトを使う必要がある。
df_dict = {}
with ZipFile(zipfile_buffer) as zip: 
    name_list = zip.namelist()
    for f in name_list:
        bytes_data = zip.read(f) # バイト形式に変換(このままじゃ読み取れない)
        df_dict[f] = pl.read_csv(io.BytesIO(bytes_data)) # BytesIOでバイト形式をファイルライクオブジェクトにしてplが読み込める形にする

for file_name, df_obj in df_dict.items():
# 作成したDataFrameをSnowflakeのデータベースに保管する
    print(f"reading {file_name}......")
    pd_df = df_obj.to_pandas()
    db_name = "KAGGLE_OLIST"
    schema_name = "PUBLIC"
    table_name = file_name.split('.')[:-1][0].upper()

    session.write_pandas(
        database = db_name,
        schema = schema_name,
        table_name = table_name,
        auto_create_table = True,
        df = pd_df,
        overwrite = True,
    )
    
print('Finished creating raw tables')