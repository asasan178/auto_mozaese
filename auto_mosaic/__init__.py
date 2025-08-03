"""
自動モザエセ v1.0 - 男女局部モザイク処理ツール (イラスト専用)

アニメ・イラスト画像の男女局部を自動検出してモザイク処理を適用するツール。
YOLO検出 + SAM分割の高精度処理により、自然な仕上がりを実現。
FANZA基準対応の安全なモザイク処理。

主要機能:
- 自動局部検出（penis, pussy, testicles, anus）
- SAMによる高精度マスク生成
- シームレスモザイク処理（境界線なし）
- FANZA基準タイル計算
- 範囲拡張機能
"""

__version__ = "1.0.0"
__author__ = "自動モザエセ開発チーム"
__description__ = "Automatic genital mosaic tool for anime/illustration images"

import sys
import logging
from pathlib import Path

# Python version check
if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10 or higher is required")

# PyTorch compatibility setup for model loading
try:
    import torch
    import torch.serialization
    import os
    import warnings
    
    # Disable weights_only warnings globally
    warnings.filterwarnings("ignore", message="Weights only load failed.*")
    warnings.filterwarnings("ignore", message=".*WeightsUnpickler.*")
    warnings.filterwarnings("ignore", message=".*torch.load.*weights_only.*")
    
    # Set global environment variable
    os.environ["PYTORCH_WEIGHTS_ONLY"] = "false"
    
    # Force disable weights_only default
    try:
        torch.serialization._weights_only_pickle_default = False
    except AttributeError:
        pass
        
    # Global override for torch.load
    _original_torch_load = torch.load
    def _global_patched_torch_load(f, *args, **kwargs):
        kwargs['weights_only'] = False
        return _original_torch_load(f, *args, **kwargs)
    torch.load = _global_patched_torch_load
    
except ImportError:
    # PyTorch not available yet, will be handled later
    pass

# ログの初期化はutils.pyの自動モザエセLoggerに一元化 
logger = logging.getLogger(__name__)
logger.info(f"自動モザエセ v{__version__} initialized") 