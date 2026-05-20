import cv2
import pandas as pd
video_path = "frontend/data/video/sample1.mp4"
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
print(frame.shape)
cv2.imwrite(
    "frontend/outputs/images/frame01.jpg",
    frame
)
csv_path = "frontend/data/csv/mock_partition.csv"
df = pd.read_csv(csv_path)
# OVERLAY PARTITIONS

for index, row in df.iterrows():
    x = int(row["x"])
    y = int(row["y"])
    w = int(row["w"])
    h = int(row["h"])

    depth = int(row["depth"])
    if depth == 0:
        color = (0, 255, 0)

    elif depth == 1:
        color = (255, 0, 0)

    elif depth == 2:
        color = (0, 0, 255)

    else:
        color = (0, 255, 255)
    cv2.rectangle(
        frame,
        (x, y),
        (x + w, y + h),
        color,
        2
    )
output_path = "frontend/outputs/images/partition_overlay1.jpg"
cv2.imwrite(output_path, frame)
print("Overlay image saved")
print("Saved at:", output_path)
cap.release()