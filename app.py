import streamlit as st
import pandas as pd
import numpy as np
import cv2
import subprocess
import os

# ==========================================
# 1. PAGE INITIALIZATION & PATH CONFIG
# ==========================================
st.set_page_config(page_title="VVC Real-time Encoder", layout="wide")
st.title("🚀 VVC Real-time Encoding & Dynamic Visualizer")
st.markdown("Upload a standard MP4 video, select your desired Quantization Parameter (QP), and let the C++ VTM backend compute the QT-MTT partitions live.")

# Relative paths pointing to your 'backend' folder structure
ENCODER_PATH = "./backend/bin/EncoderApp"
CONFIG_PATH = "./backend/cfg/encoder_randomaccess_vtm.cfg"

# Technical parameters for the VTM encoder engine
WIDTH = 416
HEIGHT = 240
TOTAL_FRAMES = 30  # Restricted to 30 frames to guarantee fast web response
FRAME_LENGTH = int(WIDTH * HEIGHT * 1.5)

# Temporary workspace filenames
INPUT_MP4 = "live_input.mp4"
INPUT_YUV = "live_input.yuv"
OUTPUT_VVC = "live_output.vvc"
LIVE_CSV   = "partition_log.csv"

# ==========================================
# 2. SIDEBAR - LIVE CONTROL PANEL
# ==========================================
st.sidebar.header("1. Target Video Input")
uploaded_mp4 = st.sidebar.file_uploader("Upload an MP4 Video", type=["mp4"])

st.sidebar.header("2. Codec Hyperparameters")
selected_qp = st.sidebar.selectbox("Select Quantization Parameter (QP):", [22, 27, 32, 37], index=2)

# ==========================================
# 3. AUTOMATED BACKEND PROCESSING PIPELINE
# ==========================================
if uploaded_mp4 is not None:
    st.sidebar.success("Original MP4 loaded into web buffer.")
    
    # Trigger button to start the heavy computation
    if st.sidebar.button("Launch VVC Live Encoding"):
        
        # STAGE A: Save uploaded stream to local disk
        with open(INPUT_MP4, "wb") as f:
            f.write(uploaded_mp4.getbuffer())
            
        # STAGE B: Convert MP4 to Raw YUV 4:2:0 via FFmpeg system call
        with st.spinner("Stage 1/2: Extracting raw YUV planar data via FFmpeg..."):
            ffmpeg_cmd = f"ffmpeg -y -i {INPUT_MP4} -vf scale={WIDTH}:{HEIGHT} -frames:v {TOTAL_FRAMES} -pix_fmt yuv420p {INPUT_YUV}"
            res_ffmpeg = subprocess.run(ffmpeg_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if res_ffmpeg.returncode != 0:
                st.error("FFmpeg execution crashed. Verify system binary paths.")
                st.stop()
        st.success("Stage 1/2 Complete: Raw YUV frame sequence prepared.")

        # STAGE C: Invoke C++ VTM EncoderApp for live RDO analysis
        with st.spinner("Stage 2/2: Activating C++ VTM Engine (Computing RDO Blocks)... This may take a minute."):
            # Erase any leftover tracking logs from previous sessions
            if os.path.exists(LIVE_CSV):
                os.remove(LIVE_CSV)
                
            # Construct the terminal execution command pointing to your backend
            vtm_cmd = f"{ENCODER_PATH} -c {CONFIG_PATH} -i {INPUT_YUV} -wdt {WIDTH} -hgt {HEIGHT} -fr 30 -f {TOTAL_FRAMES} -q {selected_qp} -b {OUTPUT_VVC}"
            res_vtm = subprocess.run(vtm_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Check if your custom C++ code successfully dropped the coordinates log
            if not os.path.exists(LIVE_CSV):
                st.error("C++ Encoder finished but failed to drop 'partition_log.csv'. Verify your C++ code injection.")
                st.stop()
                
        st.balloons()
        st.success("Pipeline executed successfully! Fresh metadata generated.")

# ==========================================
# 4. DYNAMIC VISUALIZATION VIEWPORT
# ==========================================
st.write("### 3. Generated Partition Grid Map")

# Render UI only if both the live generated CSV and YUV are present on disk
if os.path.exists(LIVE_CSV) and os.path.exists(INPUT_YUV):
    
    # Load the fresh coordinates database
    vtm_columns = ['POC', 'X', 'Y', 'W', 'H', 'QT_Depth', 'MT_Depth', 'Mode']
    df = pd.read_csv(LIVE_CSV, names=vtm_columns)
    available_pocs = sorted(df['POC'].unique())
    
    # Dynamic timeline browser slider
    selected_poc = st.slider("Timeline Browser (Frame POC):", min_value=int(available_pocs[0]), max_value=int(available_pocs[-1]), step=1)
    
    # Read the exact frame chunk from the raw YUV file
    with open(INPUT_YUV, "rb") as f:
        f.seek(selected_poc * FRAME_LENGTH)
        raw_bytes = f.read(FRAME_LENGTH)
        
        if len(raw_bytes) == FRAME_LENGTH:
            # Map byte stream to 2D image matrix
            yuv_matrix = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
            bgr_frame = cv2.cvtColor(yuv_matrix, cv2.COLOR_YUV2BGR_I420)
            
            # Filter layout data for the selected frame
            df_frame = df[df['POC'] == selected_poc]
            
            # Overlay bounding rectangles
            for _, row in df_frame.iterrows():
                x, y = int(row["X"]), int(row["Y"])
                w, h = int(row["W"]), int(row["H"])
                total_depth = int(row["QT_Depth"]) + int(row["MT_Depth"])
                
                if total_depth == 0:    color = (255, 255, 255) # White
                elif total_depth == 1:  color = (255, 200, 0)   # Cyan
                elif total_depth == 2:  color = (0, 255, 0)     # Green
                elif total_depth == 3:  color = (0, 165, 255)   # Orange
                else:                   color = (0, 0, 255)     # Red
                    
                cv2.rectangle(bgr_frame, (x, y), (x + w, y + h), color, 1)
            
            # Browser visualization sync (BGR to RGB)
            st.image(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB), caption=f"VVC Live Analysis - Frame POC: {selected_poc} | Active CUs: {len(df_frame)}", use_column_width=True)
else:
    st.info("💡 Dashboard Idle. Upload an MP4 video file and click 'Launch VVC Live Encoding' to compute block grids on-the-fly.")