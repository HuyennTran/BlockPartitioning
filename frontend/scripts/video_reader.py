import cv2
# open video
def open_video(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise Exception(f"Cannot open:{video_path}")
    return cap