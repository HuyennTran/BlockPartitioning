import pandas as pd
import numpy as np
import cv2

csv_path = "data/csv/mock_partition.csv"

df = pd.read_csv(csv_path)

img = np.zeros((512, 512, 3), dtype=np.uint8)

for index, row in df.iterrows():

    x = int(row["x"])
    y = int(row["y"])
    w = int(row["w"])
    h = int(row["h"])

    cv2.rectangle(
        img,
        (x, y),
        (x + w, y + h),
        (0, 255, 0),
        2
    )

cv2.imwrite(
    "outputs/images/partition_overlay.jpg",
    img
)

print("Overlay image saved")