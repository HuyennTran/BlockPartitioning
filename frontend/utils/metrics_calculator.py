"""
metrics_calculator.py
Calculates quantitative metrics for VVC block partitioning analysis.
Focused on essential metrics for R-D curve analysis and partition structure evaluation.
"""
import pandas as pd
import numpy as np
from typing import Dict

class PartitionMetrics:
    """Class to compute essential metrics for VVC partition analysis."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.WIDTH = 416
        self.HEIGHT = 240
        self.FRAME_AREA = self.WIDTH * self.HEIGHT
    
    # ==========================================
    # BLOCK SHAPE & SIZE METRICS (CRITICAL FOR VVC)
    # ==========================================
    
    def get_block_shape_distribution(self) -> Dict[str, int]:
        """
        Categorizes blocks into Square (QT) and Rectangular (MTT).
        Essential metric to demonstrate VVC's superiority over HEVC.
        """
        square_blocks = len(self.df[self.df['W'] == self.df['H']])
        rect_blocks = len(self.df[self.df['W'] != self.df['H']])
        return {
            'Square (QT)': square_blocks,
            'Rectangular (MTT)': rect_blocks
        }

    def get_block_size_distribution(self) -> pd.Series:
        """Distribution of specific block sizes (WxH)."""
        block_sizes = self.df['W'].astype(str) + 'x' + self.df['H'].astype(str)
        return block_sizes.value_counts().sort_values(ascending=False)
    
    def average_block_size_pixels(self) -> float:
        """Average area of a block in pixels."""
        return (self.df['W'] * self.df['H']).mean()
    
    # ==========================================
    # PREDICTION MODE METRICS
    # ==========================================
    # Note: VTM standard defines MODE_INTER = 0, MODE_INTRA = 1
    
    def get_prediction_mode_distribution(self) -> Dict[str, int]:
        """Get count of Intra (Mode 1) and Inter (Mode 0) blocks."""
        intra_count = len(self.df[self.df['Mode'] == 1])
        inter_count = len(self.df[self.df['Mode'] == 0])
        return {
            'Intra (Mode 1)': intra_count,
            'Inter (Mode 0)': inter_count
        }
    
    def intra_ratio(self) -> float:
        """Percentage of blocks using Intra prediction (Mode 1)."""
        intra_count = len(self.df[self.df['Mode'] == 1])
        return (intra_count / len(self.df) * 100) if len(self.df) > 0 else 0
    
    def inter_ratio(self) -> float:
        """Percentage of blocks using Inter prediction (Mode 0)."""
        inter_count = len(self.df[self.df['Mode'] == 0])
        return (inter_count / len(self.df) * 100) if len(self.df) > 0 else 0
    
    # ==========================================
    # DEPTH METRICS
    # ==========================================
    
    def get_qt_depth_distribution(self) -> pd.Series:
        """Distribution of Quadtree (QT) depths."""
        return self.df['QT_Depth'].value_counts().sort_index()
    
    def get_mtt_depth_distribution(self) -> pd.Series:
        """Distribution of Multi-Type Tree (MTT) depths."""
        return self.df['MT_Depth'].value_counts().sort_index()
    
    def max_qt_depth(self) -> int:
        """Maximum QT depth in dataset."""
        return int(self.df['QT_Depth'].max()) if len(self.df) > 0 else 0
    
    def max_mtt_depth(self) -> int:
        """Maximum MTT depth in dataset."""
        return int(self.df['MT_Depth'].max()) if len(self.df) > 0 else 0
    
    # ==========================================
    # FRAME-SPECIFIC METRICS
    # ==========================================
    
    def get_frame_stats(self, poc: int) -> Dict:
        """Extract essential metrics for a specific frame (POC)."""
        df_frame = self.df[self.df['POC'] == poc]
        
        if len(df_frame) == 0:
            return {}
        
        square_count = len(df_frame[df_frame['W'] == df_frame['H']])
        rect_count = len(df_frame[df_frame['W'] != df_frame['H']])
        
        return {
            'frame_poc': poc,
            'total_cus': len(df_frame),
            'square_count': square_count,
            'rect_count': rect_count,
            'intra_count': len(df_frame[df_frame['Mode'] == 1]),
            'inter_count': len(df_frame[df_frame['Mode'] == 0]),
            'avg_block_size': (df_frame['W'] * df_frame['H']).mean(),
            'max_qt_depth': int(df_frame['QT_Depth'].max()),
            'max_mtt_depth': int(df_frame['MT_Depth'].max()),
        }
    
    # ==========================================
    # SUMMARY STATISTICS
    # ==========================================
    
    def total_cus(self) -> int:
        """Total number of coding units (CUs) in the dataset."""
        return len(self.df)
    
    def total_frames(self) -> int:
        """Total number of unique frames analyzed."""
        return len(self.df['POC'].unique())
    
    def cus_per_frame(self) -> float:
        """Average number of CUs per frame."""
        return self.total_cus() / self.total_frames() if self.total_frames() > 0 else 0
    
    def get_global_summary(self) -> Dict:
        """Get global summary statistics for the entire dataset."""
        shape_dist = self.get_block_shape_distribution()
        mode_dist = self.get_prediction_mode_distribution()
        
        return {
            'total_frames': self.total_frames(),
            'total_cus': self.total_cus(),
            'cus_per_frame': self.cus_per_frame(),
            'avg_block_size': self.average_block_size_pixels(),
            'max_qt_depth': self.max_qt_depth(),
            'max_mtt_depth': self.max_mtt_depth(),
            'square_blocks': shape_dist['Square (QT)'],
            'rect_blocks': shape_dist['Rectangular (MTT)'],
            'intra_blocks': mode_dist['Intra (Mode 1)'],
            'inter_blocks': mode_dist['Inter (Mode 0)'],
            'intra_ratio': self.intra_ratio(),
            'inter_ratio': self.inter_ratio(),
        }