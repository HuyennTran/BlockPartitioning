import streamlit as st
import pandas as pd
import numpy as np
import cv2
import subprocess
import os
import shutil
import time
import re
import sys
from pathlib import Path

# --- FIX IMPORT PATH FOR UTILS ---
# Resolve absolute path to the frontend directory to ensure utils can be imported
frontend_dir = Path(__file__).resolve().parent.parent
if str(frontend_dir) not in sys.path:
    sys.path.append(str(frontend_dir))

from utils.metrics_calculator import PartitionMetrics
# ---------------------------------

# ==========================================
# 1. PAGE INITIALIZATION
# ==========================================
st.set_page_config(page_title="VVC Real-time Encoder", layout="wide")
st.title("🚀 VVC Real-time Encoding & Dynamic Visualizer")
st.markdown("Upload MP4 → VTM Encoder → Visualize QT-MTT Partitions")

# ==========================================
# 2. PATH SETUP - ABSOLUTE PATHS (KEY FIX!)
# ==========================================
PROJECT_ROOT = Path.cwd()
ENCODER_PATH = PROJECT_ROOT / "backend" / "bin" / "EncoderApp"
CONFIG_PATH = PROJECT_ROOT / "backend" / "cfg" / "encoder_randomaccess_vtm.cfg"

# Use current directory for temp files (EncoderApp will find them)
INPUT_MP4 = PROJECT_ROOT / "live_input.mp4"
INPUT_YUV = PROJECT_ROOT / "live_input.yuv"
OUTPUT_VVC = PROJECT_ROOT / "live_output.vvc"
LIVE_CSV = PROJECT_ROOT / "partition_log.csv"

# Technical parameters
WIDTH = 416
HEIGHT = 240
TOTAL_FRAMES = 30
FRAME_LENGTH = int(WIDTH * HEIGHT * 1.5)

# ==========================================
# 3. SYSTEM CHECK
# ==========================================
@st.cache_resource
def check_system():
    """Validate dependencies"""
    errors = []
    warnings = []
    
    # Check FFmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            errors.append("FFmpeg not found or not executable")
    except:
        errors.append("FFmpeg not installed")
    
    # Check EncoderApp
    if not ENCODER_PATH.exists():
        errors.append(f"❌ EncoderApp not found at: {ENCODER_PATH}")
    else:
        if not os.access(ENCODER_PATH, os.X_OK):
            try:
                os.chmod(ENCODER_PATH, 0o755)
                st.success(f"✓ Made {ENCODER_PATH.name} executable")
            except:
                errors.append(f"Cannot make {ENCODER_PATH.name} executable")
    
    # Check Config
    if not CONFIG_PATH.exists():
        errors.append(f"❌ Config not found at: {CONFIG_PATH}")
    
    return errors, warnings

errors, warnings = check_system()

# Display status
if errors:
    st.error("### ❌ System Requirements Not Met:")
    for err in errors:
        st.error(f"• {err}")
    st.stop()

if warnings:
    for warn in warnings:
        st.warning(f"⚠️ {warn}")

# ==========================================
# 4. CLEANUP FUNCTION
# ==========================================
def cleanup_old_files():
    """Remove old temporary files"""
    for file in [INPUT_MP4, INPUT_YUV, OUTPUT_VVC, LIVE_CSV]:
        if file.exists():
            try:
                file.unlink()
            except:
                pass

# ==========================================
# 5. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("⚙️ Configuration")
uploaded_mp4 = st.sidebar.file_uploader(
    "📁 Upload MP4 Video",
    type=["mp4"],
    help="Video will be resized to 416x240"
)

selected_qp = st.sidebar.selectbox(
    "🎯 Quantization Parameter (QP):",
    [22, 27, 32, 37],
    index=2,
    help="Lower QP = better quality, higher file size"
)

st.sidebar.divider()

# Info
st.sidebar.info("""
**Process Overview:**
1. Convert MP4 → YUV420
2. Run VTM Encoder
3. Extract partitions
4. Visualize with overlays

⏱️ Estimated time: 1-3 min
""")

# ==========================================
# 6. MAIN PROCESSING PIPELINE
# ==========================================
if uploaded_mp4 is not None:
    st.sidebar.success("MP4 loaded")
    
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        run_button = st.button("▶️ RUN", key="run", help="Start encoding")
    
    with col2:
        cleanup_button = st.button("🗑️ Clean", key="clean", help="Delete temp files")
    
    with col3:
        pass
    
    if cleanup_button:
        cleanup_old_files()
        st.session_state.clear()
        st.rerun()
    
    if run_button:
        try:
            # ─────────────────────────────────────────────
            # STAGE 1: Save MP4
            # ─────────────────────────────────────────────
            progress = st.progress(0)
            status = st.status("Processing Pipeline...", expanded=True)
            
            with status:
                st.write("**Stage 1/4:** Saving MP4 file...")
                
                with open(INPUT_MP4, "wb") as f:
                    f.write(uploaded_mp4.getbuffer())
                
                st.success(f"✓ Saved: {INPUT_MP4.name}")
                progress.progress(25)
            
            # ─────────────────────────────────────────────
            # STAGE 2: Convert to YUV via FFmpeg
            # ─────────────────────────────────────────────
            with status:
                st.write("**Stage 2/4:** Converting MP4 → YUV420...")
                
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", str(INPUT_MP4),
                    "-vf", f"scale={WIDTH}:{HEIGHT}",
                    "-frames:v", str(TOTAL_FRAMES),
                    "-pix_fmt", "yuv420p",
                    str(INPUT_YUV)
                ]
                
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(PROJECT_ROOT)  # KEY: Run from project root
                )
                
                if result.returncode != 0:
                    st.error(f"❌ FFmpeg failed:\n{result.stderr[:300]}")
                    st.stop()
                
                st.success(f"✓ Created: {INPUT_YUV.name} ({INPUT_YUV.stat().st_size / 1e6:.1f} MB)")
                progress.progress(50)
            
            # ─────────────────────────────────────────────
            # STAGE 3: Run VTM Encoder
            # ─────────────────────────────────────────────
            with status:
                st.write("**Stage 3/4:** Running VTM Encoder...")
                st.write("⏳ This may take 1-2 minutes...")
                
                if LIVE_CSV.exists():
                    LIVE_CSV.unlink()
                
                vtm_cmd = [
                    str(ENCODER_PATH),
                    "-c", str(CONFIG_PATH),
                    "-i", str(INPUT_YUV),
                    "-wdt", str(WIDTH),
                    "-hgt", str(HEIGHT),
                    "-fr", "30",
                    "-f", str(TOTAL_FRAMES),
                    "-q", str(selected_qp),
                    "-b", str(OUTPUT_VVC)
                ]
                
                st.code(" ".join(vtm_cmd), language="bash")
                
                # Capture execution time for Category 4: Encoding Metrics
                start_time = time.time()
                
                result = subprocess.run(
                    vtm_cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(PROJECT_ROOT)  # KEY: Run from project root
                )
                
                encoding_time = time.time() - start_time
                
                if result.returncode != 0:
                    st.error(f"❌ VTM Encoder failed!")
                    st.error(f"**Error Output:**")
                    st.code(result.stderr[:1000], language="text")
                    st.stop()
                
                # Extract Y-PSNR and Bitrate from VTM stdout logs
                vtm_metrics = {"bitrate": "N/A", "y_psnr": "N/A"}
                match = re.search(r'\s+a\s+(\d+\.\d+)\s+(\d+\.\d+)', result.stdout)
                if match:
                    vtm_metrics["bitrate"] = float(match.group(1))
                    vtm_metrics["y_psnr"] = float(match.group(2))
                
                # Save quantitative metrics to session state
                st.session_state['encoding_time'] = encoding_time
                st.session_state['vtm_metrics'] = vtm_metrics
                st.session_state['current_qp'] = selected_qp
                
                if not LIVE_CSV.exists():
                    st.error("❌ partition_log.csv not generated!")
                    st.stop()
                
                st.success(f"✓ Generated: {LIVE_CSV.name}")
                progress.progress(75)
            
            # ─────────────────────────────────────────────
            # STAGE 4: Load data
            # ─────────────────────────────────────────────
            with status:
                st.write("**Stage 4/4:** Loading partition data...")
                
                try:
                    vtm_columns = ['POC', 'X', 'Y', 'W', 'H', 'QT_Depth', 'MT_Depth', 'Mode']
                    df = pd.read_csv(LIVE_CSV, names=vtm_columns)
                    
                    st.session_state['df'] = df
                    st.session_state['input_yuv'] = str(INPUT_YUV)
                    
                    st.success(f"✓ Loaded {len(df)} partition entries from {len(df['POC'].unique())} frames")
                    
                except Exception as e:
                    st.error(f"❌ Failed to parse CSV: {e}")
                    st.stop()
                
                progress.progress(100)
            
            st.balloons()
            st.success("🎉 Pipeline Complete!")
        
        except subprocess.TimeoutExpired:
            st.error("❌ Process timeout (>3 min)")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            import traceback
            st.code(traceback.format_exc(), language="python")

# ==========================================
# 7. VISUALIZATION & ANALYTICS DASHBOARD
# ==========================================
st.divider()
st.write("### 📊 Partition Visualization & Analytics")

if 'df' in st.session_state and 'input_yuv' in st.session_state:
    df = st.session_state['df']
    input_yuv = st.session_state['input_yuv']
    
    if os.path.exists(input_yuv):
        try:
            # Initialize the metrics calculator module
            metrics_calc = PartitionMetrics(df)
            vtm_metrics = st.session_state.get('vtm_metrics', {"bitrate": 0, "y_psnr": 0})
            
            # ---------------------------------------------------------
            # Category 4: Encoding Metrics (Global Level)
            # ---------------------------------------------------------
            st.subheader("🌍 Global Encoding Performance")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Target QP", st.session_state.get('current_qp', 'N/A'))
            m_col2.metric("Processing Time", f"{st.session_state.get('encoding_time', 0):.2f} s")
            m_col3.metric("Bitrate (kbps)", vtm_metrics.get('bitrate', 'N/A'))
            m_col4.metric("Y-PSNR (dB)", vtm_metrics.get('y_psnr', 'N/A'))
            st.divider()
            
            available_pocs = sorted(df['POC'].unique())
            
            # Frame selector
            selected_poc = st.slider(
                "🎬 Select Frame (POC):",
                min_value=int(available_pocs[0]),
                max_value=int(available_pocs[-1]),
                step=1
            )
            
            # Read YUV frame
            with open(input_yuv, "rb") as f:
                f.seek(int(selected_poc) * FRAME_LENGTH)
                raw_bytes = f.read(FRAME_LENGTH)
                
                if len(raw_bytes) == FRAME_LENGTH:
                    # Convert YUV420 to BGR
                    yuv_matrix = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
                        (int(HEIGHT * 1.5), WIDTH)
                    )
                    original_bgr = cv2.cvtColor(yuv_matrix, cv2.COLOR_YUV2BGR_I420)
                    partition_bgr = original_bgr.copy()
                    
                    # Get frame partitions
                    df_frame = df[df['POC'] == selected_poc]
                    
                    # Draw partitions
                    for _, row in df_frame.iterrows():
                        x, y = int(row["X"]), int(row["Y"])
                        w, h = int(row["W"]), int(row["H"])
                        total_depth = int(row["QT_Depth"]) + int(row["MT_Depth"])
                        
                        # Color by depth
                        colors = {
                            0: (255, 255, 255),   # White
                            1: (255, 200, 0),    # Cyan
                            2: (0, 255, 0),      # Green
                            3: (0, 165, 255),    # Orange
                        }
                        color = colors.get(total_depth, (0, 0, 255))
                        
                        # Draw
                        cv2.rectangle(
                            partition_bgr,
                            (x, y),
                            (min(x + w, WIDTH), min(y + h, HEIGHT)),
                            color,
                            1
                        )
                    
                    original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
                    partition_rgb = cv2.cvtColor(partition_bgr, cv2.COLOR_BGR2RGB)
                    
                    # ---------------------------------------------------------
                    # Category Qualitative: Perception Comparison & Visual Artifacts
                    # ---------------------------------------------------------
                    st.subheader("👁️ Qualitative Analysis (Perceptual vs. Structural)")
                    img_col1, img_col2 = st.columns(2)
                    
                    with img_col1:
                        st.markdown("**Original Reconstructed Frame**")
                        st.image(original_rgb, caption=f"Frame {selected_poc}", use_column_width=True)
                    
                    with img_col2:
                        st.markdown("**VVC Partition Overlay**")
                        st.image(partition_rgb, caption=f"Frame {selected_poc}", use_column_width=True)
                    
                    st.info("💡 **Visual Artifacts Insight:** Compare the structural overlay with the perceptual image. VVC's Rate-Distortion optimization dynamically deploys small rectangular blocks around high-motion boundaries, while grouping flat backgrounds into large blocks. Observe blocking artifacts in the reconstructed frame at high QPs.")
                    
                    # ---------------------------------------------------------
                    # Category 1 & 2: Frame-Level Structure and Type Metrics
                    # ---------------------------------------------------------
                    st.subheader("📈 Frame-Level Analytics")
                    
                    frame_stats = metrics_calc.get_frame_stats(selected_poc)
                    
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("Total Coding Units (CUs)", frame_stats.get('total_cus', len(df_frame)))
                        st.metric("QT Max Depth", frame_stats.get('max_qt_depth', int(df_frame['QT_Depth'].max())))
                        st.metric("MTT Max Depth", frame_stats.get('max_mtt_depth', int(df_frame['MT_Depth'].max())))
                    
                    with stat_col2:
                        st.markdown("**Block Type Breakdown (QT vs MTT)**")
                        # Fetch shape counts if available in updated calculator, otherwise fallback to dataframe calculation
                        square_count = frame_stats.get('square_count', len(df_frame[df_frame['W'] == df_frame['H']]))
                        rect_count = frame_stats.get('rect_count', len(df_frame[df_frame['W'] != df_frame['H']]))
                        
                        st.write(f"- 🔲 Square (Quadtree): {square_count}")
                        st.write(f"- ▯ Rectangular (Multi-Type Tree): {rect_count}")
                        if len(df_frame) > 0:
                            st.progress(rect_count / len(df_frame))
                            
                    with stat_col3:
                        st.markdown("**Prediction Mode Ratio**")
                        intra_c = frame_stats.get('intra_count', len(df_frame[df_frame['Mode'] == 0]))
                        inter_c = frame_stats.get('inter_count', len(df_frame[df_frame['Mode'] == 1]))
                        
                        st.write(f"- 🔴 Intra CUs (Mode 0): {intra_c}")
                        st.write(f"- 🔵 Inter CUs (Mode 1): {inter_c}")
                        if len(df_frame) > 0:
                            st.progress(intra_c / len(df_frame))
                    
                    # Category 1: Block Size Distribution Bar Chart
                    st.markdown("**Block Size Distribution**")
                    block_sizes = df_frame['W'].astype(str) + 'x' + df_frame['H'].astype(str)
                    st.bar_chart(block_sizes.value_counts())
        
        except Exception as e:
            st.error(f"❌ Visualization error: {e}")
            import traceback
            st.code(traceback.format_exc(), language="python")
    else:
        st.warning("⚠️ YUV file not found. Run encoding first.")

else:
    st.info("""
    ### Getting Started
    
    1. **Upload** an MP4 video (16:9 recommended)
    2. **Select** QP value (lower = better quality)
    3. **Click** ▶️ RUN button
    4. **Wait** for processing (1-3 min)
    5. **Browse** frames with slider
    
    ### Color Legend
    - 🔲 White (Depth 0-1): Large 64x64 blocks
    - 🟢 Green (Depth 2): 32x32 blocks
    - 🟠 Orange (Depth 3): 16x16 blocks
    - 🔴 Red (Depth 4+): Small 4x8, 8x4 blocks
    """)

# ==========================================
# 8. DEBUG INFO (Optional)
# ==========================================
with st.expander("🔧 Debug Info"):
    st.write(f"**Project Root:** {PROJECT_ROOT}")
    st.write(f"**EncoderApp:** {ENCODER_PATH.exists()}")
    st.write(f"**Config:** {CONFIG_PATH.exists()}")
    st.write(f"**Files:**")
    for file in [INPUT_MP4, INPUT_YUV, OUTPUT_VVC, LIVE_CSV]:
        st.write(f"  - {file.name}: {file.exists()}")