"""
metrics_calculator.py
Calculates quantitative metrics for VVC block partitioning analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple

class PartitionMetrics:
    """Class to compute structure, size, and mode statistics from VTM partition logs."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.WIDTH = 416
        self.HEIGHT = 240
        self.FRAME_AREA = self.WIDTH * self.HEIGHT
    
    # --- PARTITION STRUCTURE METRICS ---
    
    def total_cus(self) -> int:
        """Total number of coding units (CUs) in the dataset."""
        return len(self.df)
    
    def total_frames(self) -> int:
        """Total number of unique frames analyzed."""
        return len(self.df['POC'].unique())
    
    def cus_per_frame(self) -> float:
        """Average number of CUs per frame."""
        return self.total_cus() / self.total_frames() if self.total_frames() > 0 else 0
    
    def get_qt_depth_distribution(self) -> pd.Series:
        """Distribution of Quadtree (QT) depths."""
        return self.df['QT_Depth'].value_counts().sort_index()
    
    def get_mtt_depth_distribution(self) -> pd.Series:
        """Distribution of Multi-Type Tree (MTT) depths."""
        return self.df['MT_Depth'].value_counts().sort_index()
    
    # --- BLOCK SHAPE & SIZE METRICS (CRITICAL FOR VVC) ---
    
    def get_block_shape_distribution(self) -> Dict[str, int]:
        """
        Categorizes blocks into Square (QT) and Rectangular (MTT).
        This is a mandatory metric to demonstrate VVC's superiority over HEVC.
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
    
    # --- PREDICTION MODE METRICS ---
    
    def intra_ratio(self) -> float:
        """Percentage of blocks using Intra prediction (Mode 0)."""
        intra_count = len(self.df[self.df['Mode'] == 0])
        return (intra_count / len(self.df) * 100) if len(self.df) > 0 else 0
    
    def inter_ratio(self) -> float:
        """Percentage of blocks using Inter prediction (Mode 1)."""
        inter_count = len(self.df[self.df['Mode'] == 1])
        return (inter_count / len(self.df) * 100) if len(self.df) > 0 else 0
    
    # --- FRAME-SPECIFIC METRICS ---
    
    def get_frame_stats(self, poc: int) -> Dict:
        """Extract all essential metrics for a specific frame (POC)."""
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
            'intra_count': len(df_frame[df_frame['Mode'] == 0]),
            'inter_count': len(df_frame[df_frame['Mode'] == 1]),
            'avg_block_size': (df_frame['W'] * df_frame['H']).mean(),
            'max_qt_depth': int(df_frame['QT_Depth'].max()),
            'max_mtt_depth': int(df_frame['MT_Depth'].max()),
        }