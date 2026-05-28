import cv2

from config import VIDEO_DIR
from config import VIDEO_FILE
from config import CSV_DIR
from config import QP_CSV
from video_reader import open_video
from parse import load_partition_data
from parse import get_blocks_by_poc
from overlay import draw_blocks
from rd_analysis import analyze_frame
# main function
def main():
    # select qp
    qp = int(input("SelectQP(22/27/32/37):"))
    # validate qp
    if qp not in QP_CSV:
        print("InvalidQP")
        return
    # build paths
    video_path = VIDEO_DIR / VIDEO_FILE
    csv_path = CSV_DIR / QP_CSV[qp]
    print(f"Video:{video_path}")
    print(f"CSV:{csv_path}")
    # load csv
    df = load_partition_data(csv_path)
    # open video
    cap = open_video(video_path)
    frame_idx = 0
    paused = False
    while True:
        if not paused:
            ret,frame = cap.read()
            if not ret:
                break
            # get current frame blocks
            blocks = get_blocks_by_poc(df,frame_idx)
            # frame analysis
            analyze_frame(blocks)
            # draw overlay
            frame = draw_blocks(frame,blocks)
            # show info
            cv2.putText(
                frame,
                f"QP:{qp} POC:{frame_idx}",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255,255,255),
                2
            )
        # show frame
        cv2.imshow(
            "BlockPartitionViewer",
            frame
        )
        key = cv2.waitKey(30)
        # quit
        if key == ord('q'):
            break
        # pause
        elif key == ord(' '):
            paused = not paused
        frame_idx += 1
    cap.release()
    cv2.destroyAllWindows()
# entry point
if __name__ == "__main__":
    main()