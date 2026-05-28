import streamlit as st
import pandas as pd
import numpy as np
import cv2
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.metrics_calculator import PartitionMetrics
from utils.shared import read_yuv_frame, draw_partitions, load_partition_csv

st.set_page_config(page_title="Sample Data", layout="wide")
st.title("📊 Sample Data Visualization & Analysis")

# ═══════════════════════════════════════════════════════════════════
# LOAD SAMPLE DATA
# ═══════════════════════════════════════════════════════════════════

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples"
SAMPLE_CSV = Path(__file__).parent.parent.parent / "backend" / "sample_data" / "csv" / "foreman_qp27_partition.csv"
SAMPLE_YUV = Path(__file__).parent.parent.parent / "backend" / "foreman.yuv"

WIDTH = 416
HEIGHT = 240
FRAME_LENGTH = int(WIDTH * HEIGHT * 1.5)

@st.cache_data
def load_data():
    """Load sample CSV and calculate metrics"""
    if not SAMPLE_CSV.exists():
        st.error(f"❌ CSV not found: {SAMPLE_CSV}")
        st.stop()
    
    df = load_partition_csv(SAMPLE_CSV)
    metrics = PartitionMetrics(df)
    return df, metrics

df, metrics = load_data()

st.success(f"✅ Loaded {len(df):,} partitions from {metrics.total_frames()} frames")

# ═══════════════════════════════════════════════════════════════════
# TABS: Navigation
# ═══════════════════════════════════════════════════════════════════

tab_summary, tab_visualization, tab_analysis, tab_details = st.tabs([
    "📈 Summary",
    "🎬 Visualization",
    "📊 Analysis",
    "📋 Details"
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: SUMMARY METRICS
# ═══════════════════════════════════════════════════════════════════

with tab_summary:
    st.header("📊 Overall Statistics")
    
    summary = metrics.get_summary()
    
    # ─────────────────────────────────────────────
    # Key Metrics Cards
    # ─────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📦 Total CUs",
            f"{summary['total_cus']:,}",
            help="Total Coding Units"
        )
    
    with col2:
        st.metric(
            "🎬 Total Frames",
            summary['total_frames'],
            help="Number of frames analyzed"
        )
    
    with col3:
        st.metric(
            "⏬ CUs/Frame",
            f"{summary['cus_per_frame']:.0f}",
            help="Average CUs per frame"
        )
    
    with col4:
        st.metric(
            "📏 Avg Block Size",
            f"{summary['avg_block_size']:.0f} px²",
            help="Average block area in pixels"
        )
    
    # ─────────────────────────────────────────────
    # Prediction Mode
    # ─────────────────────────────────────────────
    st.subheader("🎯 Prediction Mode Distribution")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🟦 Intra (Mode 0)",
            f"{summary['intra_ratio']:.1f}%",
            help="I-frame prediction percentage"
        )
    
    with col2:
        st.metric(
            "🟩 Inter (Mode 1)",
            f"{summary['inter_ratio']:.1f}%",
            help="Inter frame prediction percentage"
        )
    
    with col3:
        mode_dist = metrics.get_mode_distribution()
        st.metric(
            "Coverage",
            f"{metrics.frame_coverage():.1f}%",
            help="Frame area covered by partitions"
        )
    
    # ─────────────────────────────────────────────
    # Depth Analysis
    # ─────────────────────────────────────────────
    st.subheader("🌳 Tree Depth Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Max QT Depth",
            summary['max_qt_depth'],
            help="Maximum Quadtree subdivision level"
        )
    
    with col2:
        st.metric(
            "🔀 Max MTT Depth",
            summary['max_mtt_depth'],
            help="Maximum Multi-Type Tree subdivision level"
        )
    
    with col3:
        st.metric(
            "📈 Max Total Depth",
            summary['max_total_depth'],
            help="Combined QT + MTT maximum depth"
        )
    
    # ─────────────────────────────────────────────
    # Detailed Statistics Table
    # ─────────────────────────────────────────────
    st.subheader("📋 Detailed Summary Table")
    
    summary_df = pd.DataFrame([
        {"Metric": "Total Coding Units", "Value": f"{summary['total_cus']:,}"},
        {"Metric": "Total Frames", "Value": summary['total_frames']},
        {"Metric": "CUs per Frame", "Value": f"{summary['cus_per_frame']:.2f}"},
        {"Metric": "Average Block Size (px²)", "Value": f"{summary['avg_block_size']:.2f}"},
        {"Metric": "Frame Coverage (%)", "Value": f"{metrics.frame_coverage():.2f}%"},
        {"Metric": "Intra Ratio (%)", "Value": f"{summary['intra_ratio']:.2f}%"},
        {"Metric": "Inter Ratio (%)", "Value": f"{summary['inter_ratio']:.2f}%"},
        {"Metric": "Max QT Depth", "Value": summary['max_qt_depth']},
        {"Metric": "Max MTT Depth", "Value": summary['max_mtt_depth']},
        {"Metric": "Max Total Depth", "Value": summary['max_total_depth']},
    ])
    
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════���
# TAB 2: VISUALIZATION
# ═══════════════════════════════════════════════════════════════════

with tab_visualization:
    st.header("🎬 Frame Visualization")
    
    available_pocs = sorted(df['POC'].unique())
    
    selected_poc = st.slider(
        "Select Frame (POC):",
        min_value=int(available_pocs[0]),
        max_value=int(available_pocs[-1]),
        step=1
    )
    
    if SAMPLE_YUV.exists():
        try:
            with open(SAMPLE_YUV, "rb") as f:
                f.seek(int(selected_poc) * FRAME_LENGTH)
                raw_bytes = f.read(FRAME_LENGTH)
                
                if len(raw_bytes) == FRAME_LENGTH:
                    yuv_matrix = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
                        (int(HEIGHT * 1.5), WIDTH)
                    )
                    bgr_frame = cv2.cvtColor(yuv_matrix, cv2.COLOR_YUV2BGR_I420)
                    
                    df_frame = df[df['POC'] == selected_poc]
                    bgr_frame = draw_partitions(bgr_frame, df_frame)
                    
                    col_img, col_stats = st.columns([3, 1])
                    
                    with col_img:
                        st.image(
                            cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB),
                            caption=f"Frame POC: {selected_poc}",
                            use_column_width=True
                        )
                    
                    with col_stats:
                        frame_stats = metrics.get_frame_stats(selected_poc)
                        st.metric("CUs", frame_stats['total_cus'])
                        st.metric("Intra", frame_stats['intra_count'])
                        st.metric("Inter", frame_stats['inter_count'])
                        st.metric("Intra %", f"{frame_stats['intra_ratio']:.1f}%")
                        st.metric("Avg Size", f"{frame_stats['avg_block_size']:.0f} px²")
                        st.metric("QT Depth", frame_stats['max_qt_depth'])
                        st.metric("MTT Depth", frame_stats['max_mtt_depth'])
        
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("YUV file not found")
        df_frame = df[df['POC'] == selected_poc]
        st.dataframe(df_frame, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 3: ANALYSIS CHARTS
# ═══════════════════════════════════════════════════════════════════

with tab_analysis:
    st.header("📊 Detailed Analysis")
    
    # ─────────────────────────────────────────────
    # QT Depth Distribution
    # ─────────────────────────────────────────────
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌳 QT Depth Distribution")
        qt_dist = metrics.get_qt_depth_distribution()
        st.bar_chart(qt_dist)
    
    with col2:
        st.subheader("🔀 MTT Depth Distribution")
        mtt_dist = metrics.get_mtt_depth_distribution()
        st.bar_chart(mtt_dist)
    
    # ─────────────────────────────────────────────
    # Total Depth Distribution
    # ─────────────────────────────────────────────
    st.subheader("📈 Total Depth (QT + MTT)")
    total_depth_dist = metrics.get_total_depth_distribution()
    st.bar_chart(total_depth_dist)
    
    # ─────────────────────────────────────────────
    # Block Size Distribution
    # ─────────────────────────────────────────────
    st.subheader("📏 Block Size Distribution")
    
    block_sizes = metrics.get_block_size_summary()
    block_df = pd.DataFrame(list(block_sizes.items()), columns=['Size', 'Count'])
    block_df = block_df[block_df['Count'] > 0].sort_values('Count', ascending=False)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.bar_chart(block_df.set_index('Size')['Count'])
    
    with col2:
        st.dataframe(block_df, use_container_width=True, hide_index=True)
    
    # ─────────────────────────────────────────────
    # Mode Distribution Pie Chart
    # ─────────────────────────────────────────────
    st.subheader("🎯 Prediction Mode Distribution")
    
    mode_data = metrics.get_mode_distribution()
    mode_df = pd.DataFrame(list(mode_data.items()), columns=['Mode', 'Count'])
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.bar_chart(mode_df.set_index('Mode')['Count'])
    
    with col2:
        st.dataframe(mode_df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 4: DETAILED DATA
# ═══════════════════════════════════════════════════════════════════

with tab_details:
    st.header("📋 Raw Data Browser")
    
    # Frame selector
    selected_poc_detail = st.selectbox(
        "Select Frame:",
        sorted(df['POC'].unique())
    )
    
    df_selected = df[df['POC'] == selected_poc_detail]
    
    st.subheader(f"Frame {selected_poc_detail} - All Partitions")
    st.dataframe(df_selected, use_container_width=True, height=400)
    
    # Export button
    csv_data = df_selected.to_csv(index=False)
    st.download_button(
        label="📥 Download Frame Data (CSV)",
        data=csv_data,
        file_name=f"frame_{selected_poc_detail}_partitions.csv",
        mime="text/csv"
    )
    
    # Full dataset statistics
    st.subheader("📊 Full Dataset Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Rows", len(df))
    
    with col2:
        st.metric("Data Types", len(df.dtypes))
    
    with col3:
        st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1e6:.2f} MB")
    
    # Column statistics
    st.subheader("📈 Column Statistics")
    st.dataframe(df.describe(), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════

st.divider()

with st.expander("ℹ️ About This Data"):
    st.markdown("""
    **Block Partitioning Study**
    
    This analysis visualizes VVC (Versatile Video Coding) block partition decisions:
    
    - **QT (Quadtree)**: Hierarchical 1:4 splitting of coding units
    - **MTT (Multi-Type Tree)**: 1:2 horizontal or vertical splitting
    - **CU (Coding Unit)**: Smallest unit in partition tree
    
    **Color Legend:**
    - 🔲 White: Depth 0-1 (Large blocks)
    - 🟢 Green: Depth 2 (32×32 blocks)
    - 🟠 Orange: Depth 3 (16×16 blocks)
    - 🔴 Red: Depth 4+ (Small blocks)
    
    **Data Source:** Foreman sequence @ QP=27
    """)