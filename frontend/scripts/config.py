from pathlib import Path
# root
BASE_DIR = Path(__file__).resolve().parent
# backend path
ROOT_DIR = BASE_DIR.parent.parent
# sample data
DATA_DIR = ROOT_DIR / "backend" / "sample_data"
# video folder
VIDEO_DIR = DATA_DIR / "video"
# csv folder
CSV_DIR = DATA_DIR / "csv"
# default video
VIDEO_FILE = "sample1.mp4"
# qp csv mapping
QP_CSV = {
    22:"foreman_qp22_partition.csv",
    27:"foreman_qp27_partition.csv",
    32:"foreman_qp32_partition.csv",
    37:"foreman_qp37_partition.csv"
}