import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
from pathlib import Path
import sys
import re
import matplotlib.pyplot as plt

# --- FIX IMPORT PATH FOR UTILS ---
frontend_dir = Path(__file__).resolve().parent.parent
if str(frontend_dir) not in sys.path:
    sys.path.append(str(frontend_dir))

from utils.metrics_calculator import PartitionMetrics
# ---------------------------------

# ==========================================
# 1. PAGE INITIALIZATION
# ==========================================
st.set_page_config(page_title="VVC Sample Visualizer", layout="wide")
st.title("📊 VVC Sample Data Visualizer")
st.markdown("Select pre-existing samples → Compare R-D across QP values → Analyze partition structure")

# ==========================================
# 2. PATH SETUP & GLOBALS
# ==========================================
PROJECT_ROOT = Path.cwd()
SAMPLES_DIR = PROJECT_ROOT / "samples"
AVAILABLE_QP = [22, 27, 32, 37]

# Standard Academic YUV Resolutions
STANDARD_RES = {
    "QCIF (176x144)": (176, 144),
    "CIF (352x288)": (352, 288),
    "Class D (416x240)": (416, 240),
    "VGA (640x480)": (640, 480),
    "Class C (832x480)": (832, 480),
    "HD (1280x720)": (1280, 720),
    "FHD (1920x1080)": (1920, 1080)
}

# ==========================================
# 3. METADATA HELPER FUNCTIONS
# ==========================================
def parse_vtm_log(log_path):
    """Extract Bitrate and Y-PSNR from VTM terminal log (.txt)"""
    if not log_path or not Path(log_path).exists():
        return None
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines):
                match = re.search(r'a\s+([0-9.]+)\s+([0-9.]+)', line)
                if match:
                    return {'bitrate': float(match.group(1)), 'psnr': float(match.group(2))}
    except Exception:
        pass
    return None

def detect_resolution_from_filesize(yuv_path):
    """Mathematically deduce YUV resolution based on byte divisibility"""
    if not yuv_path or not os.path.exists(yuv_path):
        return "Class D (416x240)" # Fallback
        
    fsize = os.path.getsize(yuv_path)
    
    # Check from largest to smallest to avoid false subset matches
    for name in reversed(list(STANDARD_RES.keys())):
        w, h = STANDARD_RES[name]
        frame_size = w * h * 1.5 # 1.5 bytes per pixel for YUV420p
        if fsize % frame_size == 0:
            return name
            
    return "Class D (416x240)" # Default Fallback

# ==========================================
# 4. DISCOVER AVAILABLE SAMPLES
# ==========================================
@st.cache_data
def discover_samples():
    samples = {}
    if not SAMPLES_DIR.exists(): return samples
    for sample_dir in SAMPLES_DIR.iterdir():
        if sample_dir.is_dir():
            csv_files = list(sample_dir.glob("*_qp*_partition.csv"))
            if not csv_files: continue
            first_csv_name = csv_files[0].name
            video_name = first_csv_name.split('_qp')[0]
            yuv_file = sample_dir / f"{video_name}.yuv"
            qp_files = {}
            all_exist = True
            for qp in AVAILABLE_QP:
                csv_path = sample_dir / f"{video_name}_qp{qp}_partition.csv"
                log_path = sample_dir / f"terminal_log_{video_name}_qp{qp}.txt"
                if csv_path.exists():
                    qp_files[qp] = {
                        'csv_path': str(csv_path),
                        'log_path': str(log_path) if log_path.exists() else None,
                        'yuv_path': str(yuv_file) if yuv_file.exists() else None
                    }
                else: all_exist = False
            if all_exist: samples[sample_dir.name] = qp_files
    return samples

# ==========================================
# 5. BUILD R-D DATA FOR SAMPLE
# ==========================================
@st.cache_data
def build_rd_data_for_sample(sample_name):
    rd_data = []
    sample_data = discover_samples().get(sample_name, {})
    for qp, paths in sample_data.items():
        if paths['log_path']:
            metadata = parse_vtm_log(paths['log_path'])
            if metadata and 'bitrate' in metadata and 'psnr' in metadata:
                rd_data.append({'qp': qp, 'bitrate': metadata['bitrate'], 'psnr': metadata['psnr']})
    return rd_data

# ==========================================
# 6. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("⚙️ Sample & QP Selection")

available_samples = discover_samples()
if not available_samples:
    st.error("❌ No valid samples found. Ensure CSV files and logs exist in `samples/`.")
    st.stop()

sample_names = sorted(available_samples.keys())
selected_sample = st.sidebar.selectbox("🎯 Select Sample:", sample_names)

selected_qp = st.sidebar.slider(
    "🎚️ Quantization Parameter (QP):",
    min_value=min(AVAILABLE_QP), max_value=max(AVAILABLE_QP),
    value=32, step=5
)

nearest_qp = min(AVAILABLE_QP, key=lambda x: abs(x - selected_qp))
if nearest_qp != selected_qp: selected_qp = nearest_qp

st.sidebar.divider()

sample_data = available_samples[selected_sample]
qp_info = sample_data[selected_qp]

# --- RESOLUTION AUTO-DETECTOR UI ---
st.sidebar.subheader("📐 Resolution Settings")
st.sidebar.caption("System mathematically auto-detected resolution from file size.")

# Auto-detect using the YUV file
detected_res = detect_resolution_from_filesize(qp_info['yuv_path'])

# Dropdown for resolution (Auto-selects the mathematically correct one)
selected_res_name = st.sidebar.selectbox(
    "Video Resolution:",
    list(STANDARD_RES.keys()),
    index=list(STANDARD_RES.keys()).index(detected_res)
)

# Extract Width and Height
custom_width, custom_height = STANDARD_RES[selected_res_name]

st.sidebar.divider()

# ==========================================
# 7. LOAD & PROCESS SAMPLE DATA
# ==========================================
try:
    csv_path = qp_info['csv_path']
    yuv_path = qp_info['yuv_path']
    
    vtm_columns = ['POC', 'X', 'Y', 'W', 'H', 'QT_Depth', 'MT_Depth', 'Mode']
    df = pd.read_csv(csv_path, names=vtm_columns)
    
    # Use explicitly selected dimensions
    frame_length = int(custom_width * custom_height * 1.5)
    
    st.session_state['df'] = df
    st.session_state['input_yuv'] = yuv_path
    st.session_state['selected_sample'] = selected_sample
    st.session_state['selected_qp'] = selected_qp
    
except Exception as e:
    st.error(f"❌ Failed to load sample: {e}")
    st.stop()

# ==========================================
# 8. R-D CURVE SECTION
# ==========================================
st.divider()
st.write("### 📈 Rate-Distortion (R-D) Analysis")

rd_data = build_rd_data_for_sample(selected_sample)

if rd_data:
    rd_df = pd.DataFrame(rd_data).sort_values('bitrate')
    rd_col1, rd_col2 = st.columns([3, 1])
    
    with rd_col1:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.scatter(rd_df['bitrate'], rd_df['psnr'], s=200, color='#1f77b4', edgecolors='#0d47a1', linewidth=2.5, zorder=3, alpha=0.8)
        for idx, row in rd_df.iterrows():
            ax.annotate(f"QP {int(row['qp'])}", (row['bitrate'], row['psnr']), xytext=(8, 8), textcoords='offset points', fontsize=11, weight='bold', bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow', alpha=0.4))
        ax.plot(rd_df['bitrate'], rd_df['psnr'], 'k--', alpha=0.3, linewidth=1.5)
        ax.set_xlabel('Bitrate (kbps)', fontsize=12, weight='bold')
        ax.set_ylabel('Y-PSNR (dB)', fontsize=12, weight='bold')
        ax.set_title(f'Rate-Distortion Trade-off: {selected_sample}', fontsize=13, weight='bold')
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
            eff_display['dB/kbps'] = eff_display['dB/kbps'].round(4)
            st.dataframe(eff_display, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ R-D Log data not found or could not be parsed.")

st.divider()

# ==========================================
# 9. VISUALIZATION & ANALYSIS DASHBOARD
# ==========================================
st.write("### 👁️ Partition Visualization & Structure Analysis")

if 'df' in st.session_state and 'input_yuv' in st.session_state:
    df = st.session_state['df']
    input_yuv = st.session_state['input_yuv']
    
    if input_yuv and os.path.exists(input_yuv):
        try:
            metrics_calc = PartitionMetrics(df)
            st.subheader(f"📁 Sample: {st.session_state['selected_sample']} | QP: {st.session_state['selected_qp']}")
            st.divider()
            
            available_pocs = sorted(df['POC'].unique())
            selected_poc = st.slider("🎬 Select Frame (POC):", min_value=int(available_pocs[0]), max_value=int(available_pocs[-1]), step=1)
            
            d_width = custom_width
            d_height = custom_height
            d_frame_length = int(d_width * d_height * 1.5)
            
            with open(input_yuv, "rb") as f:
                f.seek(int(selected_poc) * d_frame_length)
                raw_bytes = f.read(d_frame_length)
                
                if len(raw_bytes) == d_frame_length:
                    yuv_matrix = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((int(d_height * 1.5), d_width))
                    original_bgr = cv2.cvtColor(yuv_matrix, cv2.COLOR_YUV2BGR_I420)
                    partition_bgr = original_bgr.copy()
                    
                    df_frame = df[df['POC'] == selected_poc]
                    
                    for _, row in df_frame.iterrows():
                        x, y, w, h = int(row["X"]), int(row["Y"]), int(row["W"]), int(row["H"])
                        
                        # --- CRITICAL FIX ---
                        # Bỏ qua khối đệm (Padding) sinh ra do hệ thống CTU của VTM tràn viền
                        if x >= d_width or y >= d_height:
                            continue
                            
                        total_depth = int(row["QT_Depth"]) + int(row["MT_Depth"])
                        colors = {0: (255, 255, 255), 1: (255, 200, 0), 2: (0, 255, 0), 3: (0, 165, 255)}
                        color = colors.get(total_depth, (0, 0, 255))
                        
                        cv2.rectangle(partition_bgr, (x, y), (min(x + w, d_width), min(y + h, d_height)), color, 1)
                    
                    original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
                    partition_rgb = cv2.cvtColor(partition_bgr, cv2.COLOR_BGR2RGB)
                    
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        st.markdown("**Original Input Frame**")
                        st.image(original_rgb, caption=f"Frame {selected_poc}", use_container_width=True)
                    with img_col2:
                        st.markdown(f"**VVC Partition Overlay (QP {selected_qp})** — Color by depth")
                        st.image(partition_rgb, caption=f"Frame {selected_poc}", use_container_width=True)
                    
                    # ---------------------------------------------------------
                    # METRICS
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
                    
                    st.markdown("**Block Size Distribution**")
                    block_sizes = df_frame['W'].astype(str) + 'x' + df_frame['H'].astype(str)
                    st.bar_chart(block_sizes.value_counts())
        
        except Exception as e:
            st.error(f"❌ Visualization error: {e}")