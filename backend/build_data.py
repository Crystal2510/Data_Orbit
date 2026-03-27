# backend/build_cloud_db.py
import os
import glob
import pandas as pd
from sqlalchemy import create_engine

CLOUD_DB_URL = "postgresql://neondb_owner:npg_91hgMFarmtNI@ep-lingering-truth-a1vskwc3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

DATA_DIR = "./data" 

def upload_to_cloud():
    print("Connecting to Neon Cloud PostgreSQL...")

    engine = create_engine(CLOUD_DB_URL)
    

    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    if not csv_files:
        print("No CSV files found in backend/data/")
        return

    for file in csv_files:
        base_name = os.path.basename(file).replace('.csv', '')
        table_name = base_name.replace('olist_', '').replace('_dataset', '')
        
        print(f"Uploading {table_name} to the cloud (this might take a minute)...")
        
        df = pd.read_csv(file)
        
        df.to_sql(table_name, con=engine, if_exists='replace', index=False, chunksize=1000)
        
    print("SUCCESS! All data is now live on the Neon cloud database!")

if __name__ == "__main__":
    upload_to_cloud()