"""Shared utilities for both modes"""
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import cv2

WIDTH = 416
HEIGHT = 240
TOTAL_FRAMES = 30
FRAME_LENGTH = int(WIDTH * HEIGHT * 1.5)

def read_yuv_frame(yuv_path, poc):
    """Read single YUV frame by POC"""
    with open(yuv_path, "rb") as f:
        f.seek(int(poc) * FRAME_LENGTH)
        raw_bytes = f.read(FRAME_LENGTH)
        
        if len(raw_bytes) != FRAME_LENGTH:
            return None
        
        yuv_matrix = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
            (int(HEIGHT * 1.5), WIDTH)
        )
        bgr_frame = cv2.cvtColor(yuv_matrix, cv2.COLOR_YUV2BGR_I420)
        return bgr_frame

def draw_partitions(frame, df_frame):
    """Draw partition rectangles on frame"""
    colors = {
        0: (255, 255, 255),
        1: (255, 200, 0),
        2: (0, 255, 0),
        3: (0, 165, 255),
    }
    
    for _, row in df_frame.iterrows():
        x, y = int(row["X"]), int(row["Y"])
        w, h = int(row["W"]), int(row["H"])
        depth = int(row["QT_Depth"]) + int(row["MT_Depth"])
        
        color = colors.get(depth, (0, 0, 255))
        
        cv2.rectangle(
            frame,
            (x, y),
            (min(x + w, WIDTH), min(y + h, HEIGHT)),
            color,
            1
        )
    
    return frame

def load_partition_csv(csv_path):
    """Load partition CSV"""
    columns = ['POC', 'X', 'Y', 'W', 'H', 'QT_Depth', 'MT_Depth', 'Mode']
    return pd.read_csv(csv_path, names=columns)