import io
import polars as pl
from pathlib import Path
from snowflake.snowpark.context import get_active_session
from zipfile import ZipFile 

# ※もし事前にテーブル作成専用の一時的な内部ステージが必要ならSQLで作成しておきます
# session.sql("CREATE OR REPLACE STAGE MY_DATA_LOAD_STAGE").collect()

session = get_active_session()
session.sql("USE DATABASE KAGGLE_OLIST").collect()
stage_abs_path = '@"KAGGLE_OLIST"."PUBLIC"."KAGGLE_OLIST"/kaggle_olist.zip'

# get_streamでデータを取得する
zipfile_buffer = session.file.get_stream(stage_abs_path, decompress=False)

# ZipFile関数はダックコードでPath, データオブジェクトどちらかを渡すことで挙動が変わる
# Pathを渡した時に挙動するのは、実行環境のディスクにデータがある場合のみ
# この環境はCOMPUTE_POOLで実行されてるので、Stageがあるのは別のディスクだからデータオブジェクトを使う必要がある。

with ZipFile(zipfile_buffer) as zip: 
    name_list = zip.namelist()

    for f_name in name_list:
        print(f"{f_name} からParquet作成中")
        # テーブル名を作成
        source_name = f_name.replace('.csv', '')
        table_name = source_name.upper()
        # zipファイルをバイト形式で読み込み
        bytes_buffer = zip.read(f_name)
    
        print(f"{f_name} からステージに格納中")
        # ファイルライクオブジェクト(BytesIO)に変換してParquetファイルとして対象のステージに格納
        pl_df = pl.read_csv(io.BytesIO(bytes_buffer))
        bytes_io = io.BytesIO() # ファイルライクオブジェクトの枠を作成
        pl_df.write_parquet(bytes_io) # polars dataframeのwrite_parquet関数を使い、ファイルライクオブジェクトにデータを.parquet形式で保存

        # [Snowflakeは自動で実施するので不必要] => バイト型ファイルを書き切った後、カーソルが最後尾になるので冒頭(0)にリセット, 慣習的な処理
        bytes_io.seek(0)

        # Uploads local files to the stage via a file stream.
        session.file.put_stream(
            input_stream = bytes_io,
            stage_location = f'@"KAGGLE_OLIST"."PUBLIC"."KAGGLE_OLIST"/{source_name}.parquet',
            auto_compress = False,
            overwrite = True
        )
        
        print(f"作成したParquetファイルからテーブルを作成")
        # 作成したSTAGEからテーブルを作成する(Snowflake環境で実施される)
        # read.parquetはSnowpark.DataFrame形式で帰ってくる、このデータのwrite系関数であるsave_as_tableを用いることで変数にDFを保持させない狙い
        session.read.parquet(
            path = f'@"KAGGLE_OLIST"."PUBLIC"."KAGGLE_OLIST"/{source_name}.parquet'
        ).write.save_as_table(
            table_name = table_name,
            mode = "overwrite"
        )
        print(f"{f_name} の テーブル格納が完了")
    
print(f"全{len(name_list)}個のファイルがテーブルとして格納されました。")