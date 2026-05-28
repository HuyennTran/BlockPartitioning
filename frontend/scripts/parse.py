import pandas as pd
# load csv
def load_partition_data(csv_path):
    df = pd.read_csv(csv_path)
    return df
# filter by poc
def get_blocks_by_poc(df,poc):
    blocks = df[df["POC"] == poc]
    return blocks