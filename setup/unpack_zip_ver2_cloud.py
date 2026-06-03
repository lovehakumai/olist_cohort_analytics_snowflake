import io
import polars as pl
from pathlib import Path

# ※もし事前にテーブル作成専用の一時的な内部ステージが必要ならSQLで作成しておきます
# session.sql("CREATE OR REPLACE STAGE MY_DATA_LOAD_STAGE").collect()

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


for file_name, pl_df in df_dict.items():
    pure_name = Path(file_name).name
    if not pure_name.endswith('.csv'):
        continue
        
    # ベースのファイル名とテーブル名を定義 (例: "olist_customers_dataset")
    base_name = pure_name.replace(".csv", "")
    table_name = base_name.upper()
    
    print(f"【超高速ロード開始】{table_name} をステージ経由で格納中...")

    # --- Step 1: Polarsオブジェクトをメモリ上でParquetバイナリにする ---
    parquet_buffer = io.BytesIO()
    
    # Pandasと違い、Polarsはメモリを無駄にコピーせず一瞬でParquetストリームに変換できます
    pl_df.write_parquet(parquet_buffer) 
    
    # ⚠️【超重要ワナ】書き込みが終わるとデータの末尾にカーソルがいるため、先頭(0)に巻き戻す
    parquet_buffer.seek(0) 

    # --- Step 2: put_stream でSnowflakeのステージへ直接アップロード ---
    # 保存先のフルパス（ステージ名の後に「/ファイル名.parquet」まで含めるのが鉄則です）
    stage_target_path = f'@"KAGGLE_OLIST"."PUBLIC"."KAGGLE_OLIST"/{base_name}.parquet'
    
    session.file.put_stream(
        input_stream=parquet_buffer,
        stage_location=stage_target_path,
        auto_compress=False,  # Parquetは元から強力に圧縮されているので、これ以上圧縮しなくてOK
        overwrite=True        # 既に同じファイルがあれば上書き
    )

    # --- Step 3: Snowflakeのパワーでテーブル化する ---
    # ローカルのPythonではなく、Snowflakeのウェアハウスを使って一瞬でParquetからテーブルに変換
    session.read.parquet(stage_target_path).write.save_as_table(
        table_name=table_name,
        mode="overwrite"
    )
    
    print(f"【成功】テーブル {table_name} がメモリ消費ほぼゼロで着地しました！\n")