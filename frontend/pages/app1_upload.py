import streamlit as st
import pandas as pd
import numpy as np
import cv2
import subprocess
import os
import time
import re
import sys
import matplotlib.pyplot as plt
from pathlib import Path

# --- FIX IMPORT PATH FOR UTILS ---
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
st.markdown("Upload MP4 → VTM Encoder → Visualize QT-MTT Partitions & Build R-D Curve")

# ==========================================
# 2. PATH SETUP - ABSOLUTE PATHS
# ==========================================
PROJECT_ROOT = Path.cwd()
ENCODER_PATH = PROJECT_ROOT / "backend" / "bin" / "EncoderApp"
CONFIG_PATH = PROJECT_ROOT / "backend" / "cfg" / "encoder_randomaccess_vtm.cfg"

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

st.sidebar.info("""
**Process Overview:**
1. Convert MP4 → YUV420
2. Run VTM Encoder
3. Extract partitions
4. Build R-D curve

⏱️ Estimated time: 1-3 min
""")

# ==========================================
# 6. MAIN PROCESSING PIPELINE
# ==========================================
if uploaded_mp4 is not None:
    st.sidebar.success("MP4 loaded")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        run_button = st.button("▶️ RUN", key="run", help="Start encoding")
    
    with col2:
        cleanup_button = st.button("🗑️ Clean", key="clean", help="Delete temp files")
    
    if cleanup_button:
        cleanup_old_files()
        st.session_state.clear()
        st.rerun()
    
    if run_button:
        try:
            progress = st.progress(0)
            status = st.status("Processing Pipeline...", expanded=True)
            
            with status:
                st.write("**Stage 1/4:** Saving MP4 file...")
                
                with open(INPUT_MP4, "wb") as f:
                    f.write(uploaded_mp4.getbuffer())
                
                st.success(f"✓ Saved: {INPUT_MP4.name}")
                progress.progress(25)
            
            with status:
                st.write("**Stage 2/4:** Converting MP4 → YUV420...")
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
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
                    cwd=str(PROJECT_ROOT)
                )
                
                if result.returncode != 0:
                    st.error(f"❌ FFmpeg failed:\n{result.stderr[:300]}")
                    st.stop()
                
                st.success(f"✓ Created: {INPUT_YUV.name} ({INPUT_YUV.stat().st_size / 1e6:.1f} MB)")
                progress.progress(50)
            
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
                
                start_time = time.time()
                
                result = subprocess.run(
                    vtm_cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(PROJECT_ROOT)
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
                
                st.session_state['encoding_time'] = encoding_time
                st.session_state['vtm_metrics'] = vtm_metrics
                st.session_state['current_qp'] = selected_qp
                
                if not LIVE_CSV.exists():
                    st.error("❌ partition_log.csv not generated!")
                    st.stop()
                
                st.success(f"✓ Generated: {LIVE_CSV.name}")
                progress.progress(75)
            
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
# 7. VISUALIZATION & R-D ANALYSIS
# ==========================================
st.divider()
st.write("### 📊 Rate-Distortion (R-D) Analysis & Partition Visualization")

if 'df' in st.session_state and 'input_yuv' in st.session_state:
    df = st.session_state['df']
    input_yuv = st.session_state['input_yuv']
    
    if os.path.exists(input_yuv):
        try:
            metrics_calc = PartitionMetrics(df)
            vtm_metrics = st.session_state.get('vtm_metrics', {"bitrate": 0, "y_psnr": 0})
            
            # ---------------------------------------------------------
            # R-D CURVE VISUALIZATION
            # ---------------------------------------------------------
            st.subheader("📈 Build R-D Curve")
            
            # Store current encoding result in session state
            if 'rd_points' not in st.session_state:
                st.session_state['rd_points'] = []
            
            current_qp = st.session_state.get('current_qp', 'N/A')
            bitrate = vtm_metrics.get('bitrate', 0)
            psnr = vtm_metrics.get('y_psnr', 0)
            
            if bitrate != 'N/A' and psnr != 'N/A' and bitrate != 0 and psnr != 0:
                # Check if this QP already exists
                existing_points = [p for p in st.session_state['rd_points'] if p['qp'] == current_qp]
                
                if not existing_points:
                    st.session_state['rd_points'].append({
                        'qp': current_qp,
                        'bitrate': bitrate,
                        'psnr': psnr
                    })
                    st.success(f"✓ Added QP {current_qp} to R-D curve (Bitrate: {bitrate:.2f} kbps, PSNR: {psnr:.2f} dB)")
                else:
                    st.info(f"QP {current_qp} already in R-D curve. Click 'Clear R-D Data' to replace it.")
            
            # Display R-D curve
            if st.session_state['rd_points']:
                rd_df = pd.DataFrame(st.session_state['rd_points'])
                rd_df = rd_df.sort_values('bitrate')
                
                rd_col1, rd_col2 = st.columns([3, 1])
                
                with rd_col1:
                    # Create scatter plot
                    fig, ax = plt.subplots(figsize=(12, 6))
                    
                    ax.scatter(rd_df['bitrate'], rd_df['psnr'], s=200, color='#FF6B6B', 
                              edgecolors='#C92A2A', linewidth=2.5, zorder=3, alpha=0.8)
                    
                    # Add QP labels to points
                    for idx, row in rd_df.iterrows():
                        ax.annotate(f"QP {int(row['qp'])}", 
                                   (row['bitrate'], row['psnr']),
                                   xytext=(8, 8), textcoords='offset points',
                                   fontsize=11, weight='bold',
                                   bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow', alpha=0.4))
                    
                    # Connect points with line
                    ax.plot(rd_df['bitrate'], rd_df['psnr'], 'k--', alpha=0.3, linewidth=1.5)
                    
                    ax.set_xlabel('Bitrate (kbps)', fontsize=12, weight='bold')
                    ax.set_ylabel('Y-PSNR (dB)', fontsize=12, weight='bold')
                    ax.set_title('Rate-Distortion Trade-off', fontsize=13, weight='bold')
                    ax.grid(True, alpha=0.3, linestyle='--')
                    ax.set_axisbelow(True)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                with rd_col2:
                    st.markdown("**R-D Points**")
                    display_df = rd_df[['qp', 'bitrate', 'psnr']].copy()
                    display_df.columns = ['QP', 'Bitrate (kbps)', 'PSNR (dB)']
                    display_df = display_df.sort_values('QP')
                    display_df['Bitrate (kbps)'] = display_df['Bitrate (kbps)'].round(2)
                    display_df['PSNR (dB)'] = display_df['PSNR (dB)'].round(2)
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Calculate efficiency
                    if len(rd_df) > 1:
                        st.markdown("**Efficiency (dB/kbps)**")
                        rd_sorted = rd_df.sort_values('bitrate')
                        br_diff = rd_sorted['bitrate'].diff().fillna(1)
                        psnr_diff = rd_sorted['psnr'].diff().fillna(0)
                        efficiency = (psnr_diff / br_diff).fillna(0)
                        
                        eff_df = rd_sorted.copy()
                        eff_df['Efficiency'] = efficiency
                        eff_display = eff_df[['qp', 'Efficiency']].copy()
                        eff_display.columns = ['QP', 'dB/kbps']
                        eff_display['dB/kbps'] = eff_display['dB/kbps'].round(3)
                        st.dataframe(eff_display, use_container_width=True, hide_index=True)
                
                # Clear button for R-D data
                if st.button("🗑️ Clear R-D Data", key="clear_rd", use_container_width=True):
                    st.session_state['rd_points'] = []
                    st.rerun()
            else:
                st.info("💡 Encode the same video with different QP values (22, 27, 32, 37) to build the R-D curve")
            
            st.divider()
            
            # ---------------------------------------------------------
            # PARTITION VISUALIZATION
            # ---------------------------------------------------------
            st.subheader("👁️ Partition Visualization & Structure Analysis")
            
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
                        
                        cv2.rectangle(
                            partition_bgr,
                            (x, y),
                            (min(x + w, WIDTH), min(y + h, HEIGHT)),
                            color,
                            1
                        )
                    
                    original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
                    partition_rgb = cv2.cvtColor(partition_bgr, cv2.COLOR_BGR2RGB)
                    
                    img_col1, img_col2 = st.columns(2)
                    
                    with img_col1:
                        st.markdown("**Reconstructed Frame**")
                        st.image(original_rgb, caption=f"Frame {selected_poc}", use_column_width=True)
                    
                    with img_col2:
                        st.markdown("**VVC Partition Overlay (QP {})** — Color by depth".format(selected_qp))
                        st.image(partition_rgb, caption=f"Frame {selected_poc}", use_column_width=True)
                    
                    # ---------------------------------------------------------
                    # FRAME-LEVEL PARTITION METRICS
                    # ---------------------------------------------------------
                    st.subheader("📊 Frame Partition Analysis")
                    
                    frame_stats = metrics_calc.get_frame_stats(selected_poc)
                    
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    
                    with stat_col1:
                        st.metric("Coding Units", frame_stats.get('total_cus', 0))
                        st.metric("Avg Block Size (px)", f"{frame_stats.get('avg_block_size', 0):.1f}")
                    
                    with stat_col2:
                        st.metric("Square Blocks", frame_stats.get('square_count', 0))
                        st.metric("Rectangular Blocks", frame_stats.get('rect_count', 0))
                    
                    with stat_col3:
                        st.metric("Intra CUs", frame_stats.get('intra_count', 0))
                        st.metric("Inter CUs", frame_stats.get('inter_count', 0))
                    
                    with stat_col4:
                        st.metric("Max QT Depth", frame_stats.get('max_qt_depth', 0))
                        st.metric("Max MTT Depth", frame_stats.get('max_mtt_depth', 0))
                    
                    # Block size distribution
                    st.markdown("**Block Size Distribution**")
                    block_sizes = df_frame['W'].astype(str) + 'x' + df_frame['H'].astype(str)
                    st.bar_chart(block_sizes.value_counts())
                    
                    # ---------------------------------------------------------
                    # GLOBAL PARTITION STATISTICS
                    # ---------------------------------------------------------
                    st.subheader("🌍 Global Partition Statistics (All Frames)")
                    
                    global_summary = metrics_calc.get_global_summary()
                    
                    global_col1, global_col2, global_col3 = st.columns(3)
                    
                    with global_col1:
                        st.metric("Total Frames", global_summary['total_frames'])
                        st.metric("Total CUs", global_summary['total_cus'])
                        st.metric("CUs per Frame", f"{global_summary['cus_per_frame']:.1f}")
                    
                    with global_col2:
                        st.metric("Total Square Blocks", global_summary['square_blocks'])
                        st.metric("Total Rect Blocks", global_summary['rect_blocks'])
                        rect_ratio = (global_summary['rect_blocks'] / global_summary['total_cus'] * 100) if global_summary['total_cus'] > 0 else 0
                        st.metric("MTT Ratio", f"{rect_ratio:.1f}%")
                    
                    with global_col3:
                        st.metric("Total Intra CUs", global_summary['intra_blocks'])
                        st.metric("Total Inter CUs", global_summary['inter_blocks'])
                        st.metric("Intra Ratio", f"{global_summary['intra_ratio']:.1f}%")
                    
                    # Average block size trend
                    st.markdown("**Average Block Size per Frame**")
                    avg_size = df.groupby('POC').apply(lambda x: (x['W'] * x['H']).mean()).reset_index()
                    avg_size.columns = ['POC', 'Avg Block Size']
                    st.line_chart(avg_size.set_index('POC')['Avg Block Size'])
        
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
    2. **Select** QP value (lower = better quality, higher bitrate)
    3. **Click** ▶️ RUN button
    4. **Wait** for processing (1-3 min)
    5. **Repeat with different QP values** to build R-D curve
    
    ### Build R-D Curve
    - Encode the same video multiple times with different QP values
    - Each encoding adds a point to the R-D curve
    - Compare rate-distortion efficiency across QP values
    
    ### Color Legend (Partition Depth)
    - 🔲 White (Depth 0-1): Large 64x64 blocks
    - 🟡 Cyan (Depth 1-2): 32x32 blocks
    - 🟢 Green (Depth 2): Medium blocks
    - 🟠 Orange (Depth 3): 16x16 blocks
    - 🔴 Red (Depth 4+): Small 4x8, 8x4 blocks
    """)

# ==========================================
# 8. DEBUG INFO
# ==========================================
with st.expander("🔧 Debug Info"):
    st.write(f"**Project Root:** {PROJECT_ROOT}")
    st.write(f"**EncoderApp:** {ENCODER_PATH.exists()}")
    st.write(f"**Config:** {CONFIG_PATH.exists()}")
    st.write(f"**Files:**")
    for file in [INPUT_MP4, INPUT_YUV, OUTPUT_VVC, LIVE_CSV]:
        st.write(f"  - {file.name}: {file.exists()}")
