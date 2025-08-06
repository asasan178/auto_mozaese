"""
Utility functions and type helpers for 自動モザエセ v1.0

共通ユーティリティ関数とデータ型の定義
"""

import logging
import os
import sys
from pathlib import Path
from typing import Tuple, List, Optional, Union
from dataclasses import dataclass
import numpy as np
import cv2
import math
import json

# GPU detection
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

# Type aliases
BBox = Tuple[int, int, int, int]  # (x1, y1, x2, y2)
BBoxWithClass = Tuple[int, int, int, int, str, str]  # (x1, y1, x2, y2, class_name, source)
Point = Tuple[int, int]
ImageArray = np.ndarray

@dataclass
class ProcessingConfig:
    """Configuration for mosaic processing"""
    
    def __init__(self):
        # Mosaic settings
        self.strength = 1.0        # Mosaic strength (0.5-3.0)
        self.feather = 5           # Edge feathering (0-20)
        self.confidence = 0.25     # Detection confidence threshold
        self.visualize = False     # Save visualization images
        
        # Detection range adjustment (in pixels)
        self.bbox_expansion = 15   # Expand detection bounding boxes by pixels (-50 to +100)
        
        # Mosaic tile size settings
        self.use_fanza_standard = True    # Use FANZA compliance standard
        self.manual_tile_size = 16        # Manual tile size in pixels (when not using FANZA)
        
        # Mosaic effect type settings (multiple selection)
        self.mosaic_types = {
            "block": True,      # ブロックモザイク（デフォルト選択）
            "gaussian": False,  # ガウスモザイク
            "white": False,     # 白塗り
            "black": False      # 黒塗り
        }
        
        # Gaussian blur specific settings
        self.gaussian_blur_radius = 8  # ガウスモザイク用のぼかし半径（px）
        
        # Device settings
        self.device_mode = "auto"  # "auto", "cpu", "gpu"
        
        # Selected model files (Anime NSFW Detection v4.0)
        self.selected_models = {
            "penis": True,
            "labia_minora": True,  # 小陰唇（anime_nsfw_v4専用）
            "labia_majora": True,  # 大陰唇（nudenet専用）
            "testicles": True,
            "anus": True,
            "nipples": False,
            "x-ray": False,
            "cross-section": False,
            "all": False
        }
        
        # SAM segmentation options
        self.sam_use_vit_b = True      # Lightweight SAM model
        self.sam_use_none = False      # No SAM segmentation (bounding box only)
        
        # Mosaic processing mode
        self.use_seamless = True       # Use seamless processing (recommended)
        self.use_legacy = False        # Use legacy individual processing
        
        # Legacy compatibility (for backwards compatibility)
        self.use_lite = True       # Always use NSFW detection models
        self.female_genital = True
        self.female_anal = True
        self.male_genital = True
        self.male_testis = True
        
        # ファイル名設定
        self.filename_mode = "prefix"    # "original", "prefix", "sequential" (デフォルト: prefix)
        self.filename_prefix = "MC_"     # プレフィックス
        self.sequential_prefix = "MC"    # 連番用プレフィックス
        self.sequential_start_number = "001"  # 連番開始番号（文字列で桁数も管理）
        
        # 個別拡張範囲設定
        self.use_individual_expansion = False  # 個別拡張範囲を使用するかどうか
        self.individual_expansions = {
            "penis": 15,
            "labia_minora": 15,  # 小陰唇
            "labia_majora": 15,  # 大陰唇
            "testicles": 15,
            "anus": 15,
            "nipples": 15,
            "x-ray": 15,
            "cross-section": 15,
            "all": 15
        }
        
        # 検出器選択設定
        self.detector_mode = "hybrid"           # "anime_only", "nudenet_only", "hybrid"
        self.use_anime_detector = True          # イラスト専用モデルを使用
        self.use_nudenet = True                 # 実写専用モデルを使用
        
        # 実写検出専用範囲調整設定
        self.use_nudenet_shrink = False         # 実写検出範囲の縮小機能を使用
        self.nudenet_shrink_values = {
            "labia_majora": -10,                # 大陰唇の縮小値（px）- 陰毛除外用
            "penis": 0,                         # 男性器の調整値（px）
            "anus": 0,                          # 肛門の調整値（px）
            "nipples": 0                        # 乳首の調整値（px）
        }
        
        # カスタムモデル設定
        self.use_custom_models = False          # カスタムモデルを使用するかどうか
        self.custom_models = {}                 # カスタムモデル設定 {"name": {"path": "", "enabled": True, "class_mapping": {}}}
        self.custom_model_class_mappings = {}   # カスタムモデルのクラスマッピング


class 自動モザエセLogger:
    """自動モザエセ用カスタムロガー（シングルトンパターン）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, name: str = "auto_mosaic"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, name: str = "auto_mosaic"):
        # シングルトンなので一度だけ初期化
        if not self._initialized:
            self.logger = logging.getLogger(name)
            self._setup_logger()
            self.__class__._initialized = True
    
    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        if self.logger.handlers:
            return  # Already configured
            
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 開発者モードかどうかを判定
        is_dev_mode = is_developer_mode()
        
        # 配布版ではコンソール出力を無効化（開発者モードは除く）
        should_show_console = self._should_show_console_output()
        
        if should_show_console:
            # Console handler with UTF-8 encoding
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            
            # Fix encoding for Windows console
            if hasattr(console_handler.stream, 'reconfigure'):
                try:
                    console_handler.stream.reconfigure(encoding='utf-8')
                except:
                    pass  # Fallback if reconfigure fails
            
            self.logger.addHandler(console_handler)
        
        # File handler (logs directory) with UTF-8 encoding - exe化対応
        # 起動時にログファイルをクリアするため、mode='w'で上書きする
        log_dir = get_logs_dir()
        log_file_path = log_dir / "auto_mosaic.log"
        file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        
        # 開発者モードとそれ以外でログレベルを分ける
        if is_dev_mode:
            file_handler.setLevel(logging.DEBUG)  # 開発者モード: 詳細情報
            self.logger.setLevel(logging.DEBUG)
        else:
            file_handler.setLevel(logging.INFO)   # 一般モード: 重要な情報のみ
            self.logger.setLevel(logging.INFO)
            
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 起動時のログクリア完了を記録
        self.logger.info("=== 自動モザエセ 新セッション開始 ===")
        self.logger.info(f"ログファイルパス: {log_file_path}")
        self.logger.info(f"開発者モード: {is_dev_mode}")
    
    def _should_show_console_output(self) -> bool:
        """
        コンソール出力を表示するかどうかを判定
        
        Returns:
            bool: コンソール出力を表示する場合True
        """
        return is_developer_mode()
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)

def get_app_root() -> Path:
    """
    Get application root directory (exe化対応)
    
    Returns:
        Path: アプリケーションのルートディレクトリ
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでexe化された場合
        app_root = Path(sys.executable).parent
    else:
        # 開発環境の場合
        app_root = Path(__file__).parent.parent.parent
    
    return app_root

def get_app_data_dir() -> Path:
    """
    Get application data directory (AppData方式 - exe化対応)
    
    Returns:
        Path: アプリケーションデータディレクトリ
    """
    if getattr(sys, 'frozen', False):
        # exe版：AppDataフォルダを使用
        app_data_dir = Path(os.getenv('APPDATA')) / "自動モザエセ"
    else:
        # 開発環境：プロジェクトルートを使用
        app_data_dir = Path(__file__).parent.parent.parent
    
    # 必要なサブディレクトリを作成
    app_data_dir.mkdir(exist_ok=True)
    (app_data_dir / "models").mkdir(exist_ok=True)
    (app_data_dir / "logs").mkdir(exist_ok=True)
    (app_data_dir / "config").mkdir(exist_ok=True)
    
    return app_data_dir

def get_resource_path(relative_path: str) -> Path:
    """
    Get resource file path (exe化対応)
    
    Args:
        relative_path: アプリケーションルートからの相対パス
        
    Returns:
        Path: リソースファイルの絶対パス
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでexe化された場合
        if hasattr(sys, '_MEIPASS'):
            # ワンファイル実行の場合（一時展開フォルダ）
            base_path = Path(sys._MEIPASS)
        else:
            # ワンディレクトリ実行の場合
            base_path = Path(sys.executable).parent
    else:
        # 開発環境の場合
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / relative_path

def get_models_dir() -> Path:
    """
    Get models directory path (AppData方式 - exe化対応)
    
    Returns:
        Path: modelsディレクトリのパス
    """
    app_data_dir = get_app_data_dir()
    models_dir = app_data_dir / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir

def get_logs_dir() -> Path:
    """
    Get logs directory path (AppData方式 - exe化対応)
    
    Returns:
        Path: logsディレクトリのパス
    """
    app_data_dir = get_app_data_dir()
    logs_dir = app_data_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def get_device_info() -> dict:
    """
    Get information about available computing devices
    
    Returns:
        dict: Device information including GPU availability and details
    """
    info = {
        "torch_available": TORCH_AVAILABLE,
        "cuda_available": False,
        "gpu_count": 0,
        "gpu_names": [],
        "current_device": "cpu",
        "memory_info": {},
        "debug_info": {}  # exe化デバッグ用
    }
    
    # exe化環境の検出
    is_frozen = getattr(sys, 'frozen', False)
    info["debug_info"]["is_frozen"] = is_frozen
    info["debug_info"]["executable_path"] = sys.executable if is_frozen else "development"
    
    if TORCH_AVAILABLE and torch is not None:
        # PyTorchの詳細情報を追加
        info["debug_info"]["torch_version"] = torch.__version__
        info["debug_info"]["torch_cuda_version"] = getattr(torch.version, 'cuda', 'None')
        
        try:
            info["cuda_available"] = torch.cuda.is_available()
            info["debug_info"]["cuda_check_success"] = True
        except Exception as e:
            info["debug_info"]["cuda_check_error"] = str(e)
            info["cuda_available"] = False
        
        if info["cuda_available"]:
            try:
                info["gpu_count"] = torch.cuda.device_count()
                info["gpu_names"] = [torch.cuda.get_device_name(i) for i in range(info["gpu_count"])]
                info["current_device"] = f"cuda:{torch.cuda.current_device()}"
            
                # Memory information for current GPU
                if info["gpu_count"] > 0:
                    memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                    memory_allocated = torch.cuda.memory_allocated(0) / (1024**3)  # GB
                    memory_cached = torch.cuda.memory_reserved(0) / (1024**3)  # GB
                    
                    info["memory_info"] = {
                        "total_gb": round(memory_total, 2),
                        "allocated_gb": round(memory_allocated, 2),
                        "cached_gb": round(memory_cached, 2),
                        "free_gb": round(memory_total - memory_cached, 2)
                    }
            except Exception as e:
                info["debug_info"]["gpu_info_error"] = str(e)
        else:
            # CUDA利用不可の詳細情報を収集
            info["debug_info"]["cuda_unavailable_reason"] = "torch.cuda.is_available() returned False"
            
            # DLLファイルの存在確認（exe化環境用）
            if is_frozen:
                import os
                exe_dir = Path(sys.executable).parent
                
                # 一般的なCUDA DLLファイルを検索
                cuda_dll_patterns = [
                    "cudart*.dll", "cublas*.dll", "curand*.dll",
                    "cusparse*.dll", "cusolver*.dll", "cufft*.dll", 
                    "cudnn*.dll", "nvrtc*.dll", "torch_cuda*.dll"
                ]
                
                found_dlls = []
                for pattern in cuda_dll_patterns:
                    for dll in exe_dir.glob(pattern):
                        found_dlls.append(dll.name)
                
                info["debug_info"]["found_cuda_dlls"] = found_dlls
                info["debug_info"]["cuda_dll_count"] = len(found_dlls)
    else:
        info["debug_info"]["torch_import_error"] = "PyTorch not available"
    
    return info

def get_recommended_device(device_mode: str = "auto") -> str:
    """
    Get recommended device based on user preference and hardware availability
    
    Args:
        device_mode: User preference ("auto", "cpu", "gpu")
        
    Returns:
        str: Device string ("cpu" or "cuda")
    """
    device_info = get_device_info()
    
    if device_mode == "cpu":
        return "cpu"
    elif device_mode == "gpu":
        if device_info["cuda_available"]:
            return "cuda"
        else:
            logger.warning("GPU mode requested but CUDA not available, falling back to CPU")
            return "cpu"
    else:  # auto
        if device_info["cuda_available"]:
            # GPU利用可能でメモリが十分（2GB以上空き）ならGPU使用
            memory_info = device_info.get("memory_info", {})
            free_memory = memory_info.get("free_gb", 0)
            if free_memory >= 2.0:
                return "cuda"
            else:
                logger.warning(f"GPU memory insufficient ({free_memory:.1f}GB free), using CPU")
                return "cpu"
        else:
            return "cpu"

def calculate_tile_size(image_shape: Tuple[int, int], strength: float = 1.0, use_fanza: bool = True, manual_size: int = 16, mosaic_type: str = "block") -> int:
    """
    Calculate mosaic tile size based on FANZA rule or manual setting
    
    FANZA基準式：
    ドット辺長 ≧ 画像長辺 × 1%（= 1/100）
    ただし最小 4px 角以上
    小数点は切り上げ
    
    Args:
        image_shape: (height, width) of the image
        strength: multiplier for tile size (only used with FANZA standard)
        use_fanza: Whether to use FANZA compliance standard
        manual_size: Manual tile size when not using FANZA standard
        mosaic_type: Type of mosaic effect ("block", "gaussian", "white", "black")
        
    Returns:
        Tile size in pixels (minimum 4) or blur radius for gaussian
    """
    if use_fanza:
        # FANZA compliance calculation
        height, width = image_shape
        long_side = max(height, width)
        
        # FANZA基準：画像長辺 × 1% （最小4px）、小数点切り上げ
        fanza_base_size = max(4, math.ceil(long_side * 0.01))  # 切り上げ
        
        # 強度による調整（切り上げ）
        base_size = max(4, math.ceil(fanza_base_size * strength))
        
        # ガウスモザイクの場合はぼかし半径に変換
        if mosaic_type == "gaussian":
            # タイルサイズの半分をぼかし半径とする（自然な見た目）
            blur_radius = max(2, base_size // 2)
            return blur_radius
        else:
            return base_size
    else:
        # Manual size (minimum 4px for safety)
        base_size = max(4, manual_size)
        
        # ガウスモザイクの場合はぼかし半径に変換
        if mosaic_type == "gaussian":
            blur_radius = max(2, base_size // 2)
            return blur_radius
        else:
            return base_size

def validate_image_path(path: Union[str, Path]) -> bool:
    """
    Validate if the path points to a supported image file
    
    Args:
        path: Path to the image file
        
    Returns:
        True if valid image file, False otherwise
    """
    if not isinstance(path, Path):
        path = Path(path)
    
    if not path.exists() or not path.is_file():
        return False
    
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    return path.suffix.lower() in supported_extensions

def get_output_path(input_path: Union[str, Path], output_dir: Optional[Path] = None, suffix: str = "_mosaic") -> Path:
    """
    Generate output path for processed image
    
    Args:
        input_path: Original image path
        output_dir: Output directory (default: same as input)
        suffix: Suffix to add to filename
        
    Returns:
        Path for the output file
    """
    input_path = Path(input_path)
    
    if output_dir is None:
        output_dir = input_path.parent
    
    output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
    return output_dir / output_name

def get_custom_output_path(input_path: Union[str, Path], output_dir: Optional[Path] = None, 
                          suffix: str = "_mosaic", config=None, counter: int = None) -> Path:
    """
    Generate custom output path based on filename settings
    
    Args:
        input_path: Original image path
        output_dir: Output directory (default: same as input)
        suffix: Suffix to add to filename
        config: ProcessingConfig object with filename settings
        counter: Current file counter for sequential naming
        
    Returns:
        Path for the output file
    """
    input_path = Path(input_path)
    
    if output_dir is None:
        output_dir = input_path.parent
    
    if config is None or config.filename_mode == "original":
        # そのまま（元のファイル名 + suffix）
        output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
    
    elif config.filename_mode == "prefix":
        # 頭にMC_つける
        output_name = f"{config.filename_prefix}{input_path.stem}{suffix}{input_path.suffix}"
    
    elif config.filename_mode == "sequential":
        # 新規に「頭文字＋連番数字」
        if counter is not None:
            # 開始番号から実際の番号を計算
            try:
                start_num = int(config.sequential_start_number)
                current_num = start_num + counter - 1  # counterは1から開始
                # 開始番号と同じ桁数でゼロパディング
                digits = len(config.sequential_start_number)
                counter_str = str(current_num).zfill(digits)
                output_name = f"{config.sequential_prefix}{counter_str}{suffix}{input_path.suffix}"
            except ValueError:
                # 開始番号が無効な場合は元ファイル名にフォールバック
                output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
        else:
            # カウンターが指定されていない場合は元ファイル名にフォールバック
            output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
    
    else:
        # 不明なモードの場合は元ファイル名にフォールバック
        output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
    
    return output_dir / output_name

def bbox_to_mask_coords(bbox: BBox, image_shape: Tuple[int, int]) -> List[Point]:
    """
    Convert bounding box to mask coordinates
    
    Args:
        bbox: (x1, y1, x2, y2) bounding box
        image_shape: (height, width) of the image
        
    Returns:
        List of (x, y) coordinates for mask
    """
    x1, y1, x2, y2 = bbox
    height, width = image_shape
    
    # Clamp coordinates to image bounds
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

def expand_bbox(bbox: BBox, expansion: int, image_shape: Tuple[int, int]) -> BBox:
    """
    Expand or contract bounding box by specified pixels
    
    Args:
        bbox: (x1, y1, x2, y2) bounding box
        expansion: Pixels to expand (positive) or contract (negative)
        image_shape: (height, width) of the image
        
    Returns:
        Expanded bounding box, clamped to image boundaries
    """
    x1, y1, x2, y2 = bbox
    height, width = image_shape
    
    # Expand/contract the bounding box
    x1_expanded = x1 - expansion
    y1_expanded = y1 - expansion
    x2_expanded = x2 + expansion
    y2_expanded = y2 + expansion
    
    # Clamp to image boundaries
    x1_expanded = max(0, min(x1_expanded, width - 1))
    y1_expanded = max(0, min(y1_expanded, height - 1))
    x2_expanded = max(0, min(x2_expanded, width - 1))
    y2_expanded = max(0, min(y2_expanded, height - 1))
    
    # Ensure valid bbox (x2 > x1, y2 > y1)
    if x2_expanded <= x1_expanded:
        # If expansion makes bbox invalid, use original with minimal adjustment
        center_x = (x1 + x2) // 2
        x1_expanded = max(0, center_x - 1)
        x2_expanded = min(width - 1, center_x + 1)
    
    if y2_expanded <= y1_expanded:
        center_y = (y1 + y2) // 2
        y1_expanded = max(0, center_y - 1)
        y2_expanded = min(height - 1, center_y + 1)
    
    return (x1_expanded, y1_expanded, x2_expanded, y2_expanded)

def expand_bboxes(bboxes: List[BBox], expansion: int, image_shape: Tuple[int, int]) -> List[BBox]:
    """
    Expand multiple bounding boxes
    
    Args:
        bboxes: List of bounding boxes
        expansion: Pixels to expand (positive) or contract (negative)  
        image_shape: (height, width) of the image
        
    Returns:
        List of expanded bounding boxes
    """
    if expansion == 0:
        return bboxes
    
    expanded_bboxes = []
    for bbox in bboxes:
        expanded_bbox = expand_bbox(bbox, expansion, image_shape)
        expanded_bboxes.append(expanded_bbox)
    
    logger.debug(f"Expanded {len(bboxes)} bounding boxes by {expansion}px")
    return expanded_bboxes

def get_mask_centroid(mask: np.ndarray) -> Tuple[int, int]:
    """
    Calculate centroid (center of mass) of a binary mask
    
    Args:
        mask: Binary mask (0/255 or 0/1)
        
    Returns:
        (center_x, center_y) coordinates of the centroid
    """
    # Convert to binary if needed
    if mask.max() > 1:
        binary_mask = (mask > 127).astype(np.uint8)
    else:
        binary_mask = mask.astype(np.uint8)
    
    # Find all non-zero pixels
    coords = np.where(binary_mask > 0)
    if len(coords[0]) == 0:
        # Empty mask, return center of image
        return mask.shape[1] // 2, mask.shape[0] // 2
    
    # Calculate centroid
    center_y = int(np.mean(coords[0]))
    center_x = int(np.mean(coords[1]))
    
    return center_x, center_y

def expand_mask_radial(mask: np.ndarray, expansion: int) -> np.ndarray:
    """
    Expand mask radially from its centroid using efficient morphological operations
    
    Args:
        mask: Binary mask to expand (0/255)
        expansion: Pixels to expand radially (positive) or contract (negative)
        
    Returns:
        Expanded mask
    """
    if expansion == 0:
        return mask.copy()
    
    # Convert to binary if needed
    if mask.max() > 1:
        binary_mask = (mask > 127).astype(np.uint8) * 255
    else:
        binary_mask = mask.astype(np.uint8) * 255
    
    # Get centroid of the original mask
    center_x, center_y = get_mask_centroid(binary_mask)
    
    if expansion > 0:
        # Expansion using morphological dilation with circular kernel
        kernel_size = expansion * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        expanded_mask = cv2.dilate(binary_mask, kernel, iterations=1)
        
        logger.debug(f"Radially expanded mask by {expansion}px using circular kernel from centroid ({center_x}, {center_y})")
        
    else:
        # Contraction using morphological erosion with circular kernel
        erosion_amount = abs(expansion)
        kernel_size = erosion_amount * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        expanded_mask = cv2.erode(binary_mask, kernel, iterations=1)
        
        logger.debug(f"Radially contracted mask by {erosion_amount}px using circular kernel from centroid ({center_x}, {center_y})")
    
    return expanded_mask

def expand_masks_radial(masks: List[np.ndarray], expansion: int) -> List[np.ndarray]:
    """
    Expand multiple masks radially from their respective centroids
    
    Args:
        masks: List of binary masks to expand
        expansion: Pixels to expand radially (positive) or contract (negative)
        
    Returns:
        List of expanded masks
    """
    if expansion == 0:
        return [mask.copy() for mask in masks]
    
    expanded_masks = []
    for i, mask in enumerate(masks):
        try:
            expanded_mask = expand_mask_radial(mask, expansion)
            expanded_masks.append(expanded_mask)
        except Exception as e:
            logger.warning(f"Failed to expand mask {i+1}: {str(e)}, using original")
            expanded_masks.append(mask.copy())
    
    logger.info(f"Radially {'expanded' if expansion > 0 else 'contracted'} {len(masks)} masks by {abs(expansion)}px")
    return expanded_masks

def create_desktop_shortcut():
    """
    Create desktop shortcut for 自動モザエセ (Windows only)
    """
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "自動モザエセ.lnk")
        target = sys.executable  # 現在のPythonパス
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.Arguments = '-m auto_mosaic'
        shortcut.WorkingDirectory = os.getcwd()
        shortcut.IconLocation = target
        shortcut.Description = "自動モザエセ v1.0 - アニメ・イラスト画像のモザイク処理ツール"
        shortcut.save()
        
        return path
        
    except ImportError:
        logger.warning("Desktop shortcut creation requires pywin32 and winshell packages")
        return None
    except Exception as e:
        logger.error(f"Failed to create desktop shortcut: {e}")
        return None

def open_models_folder():
    """
    Open models folder in file explorer
    """
    import subprocess
    import platform
    import os
    
    models_dir = get_models_dir()
    
    try:
        if platform.system() == "Windows":
            # Windowsの場合、最も確実な方法から試行
            try:
                # 方法1: os.startfile を使用（Windows専用・最も確実）
                os.startfile(str(models_dir))
                logger.info(f"Opened models folder with os.startfile: {models_dir}")
            except Exception:
                try:
                    # 方法2: start コマンドを使用（shell=True）
                    subprocess.run(f'start "" "{models_dir}"', check=True, shell=True)
                    logger.info(f"Opened models folder with start command: {models_dir}")
                except subprocess.CalledProcessError:
                    # 方法3: explorer.exe を直接使用（最後の手段）
                    subprocess.run(["explorer.exe", str(models_dir)], check=True, shell=False)
                    logger.info(f"Opened models folder with explorer.exe: {models_dir}")
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(models_dir)], check=True)
            logger.info(f"Opened models folder: {models_dir}")
        else:  # Linux
            subprocess.run(["xdg-open", str(models_dir)], check=True)
            logger.info(f"Opened models folder: {models_dir}")
        
    except Exception as e:
        logger.error(f"Failed to open models folder: {str(e)}")
        raise  # エラーを再発生させてGUIで処理できるようにする

def is_first_run() -> bool:
    """
    Check if this is the first run of the application
    
    Returns:
        bool: True if first run, False otherwise
    """
    # コマンドライン引数で強制的に初回セットアップを有効にする
    if "--first-run" in sys.argv or "--setup" in sys.argv:
        logger.info("First run setup forced by command line argument")
        return True
    
    # 環境変数での強制有効化
    if os.getenv("AUTO_MOSAIC_FIRST_RUN", "").lower() in ["true", "1", "yes"]:
        logger.info("First run setup forced by environment variable")
        return True
    
    # 環境変数で開発環境でもマーカーファイル判定を無効化可能
    if os.getenv("AUTO_MOSAIC_DEV_SKIP_FIRST_RUN", "").lower() in ["true", "1", "yes"]:
        logger.info("First run setup skipped by development environment variable")
        return False
    
    # 開発環境と本番環境両方でマーカーファイルによる判定を実行
    app_data_dir = get_app_data_dir()
    marker_file = app_data_dir / "config" / "first_run_complete"
    
    is_first = not marker_file.exists()
    
    if not getattr(sys, 'frozen', False):
        # 開発環境の場合は追加ログ
        env_type = "development"
        logger.info(f"First run check in {env_type} environment: {'first run' if is_first else 'not first run'}")
        logger.info(f"Marker file path: {marker_file}")
    else:
        # 本番環境（exe版）
        env_type = "production"
        logger.info(f"First run check in {env_type} environment: {'first run' if is_first else 'not first run'}")
    
    return is_first

def force_first_run_setup():
    """
    Force first run setup by removing the completion marker
    初回セットアップを強制実行するためのユーティリティ関数
    """
    app_data_dir = get_app_data_dir()
    marker_file = app_data_dir / "config" / "first_run_complete"
    
    if marker_file.exists():
        marker_file.unlink()
        logger.info("First run completion marker removed - setup will be shown on next start")
        return True
    else:
        logger.info("First run completion marker does not exist")
        return False

def mark_first_run_complete():
    """
    Mark first run as complete
    """
    # 環境変数で開発環境でのマーカーファイル作成を無効化可能
    if os.getenv("AUTO_MOSAIC_DEV_SKIP_FIRST_RUN", "").lower() in ["true", "1", "yes"]:
        logger.info("First run completion marker skipped by development environment variable")
        return
    
    app_data_dir = get_app_data_dir()
    config_dir = app_data_dir / "config"
    marker_file = config_dir / "first_run_complete"
    
    # 設定ディレクトリを作成（存在しない場合）
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # マーカーファイルを作成
    marker_file.write_text("1")
    
    if not getattr(sys, 'frozen', False):
        # 開発環境
        logger.info(f"First run setup completed (development environment) - marker: {marker_file}")
    else:
        # 本番環境
        logger.info(f"First run setup completed (production environment) - marker: {marker_file}")

def expand_bboxes_individual(bboxes_with_class: List[BBoxWithClass], config, image_shape: Tuple[int, int]) -> List[BBox]:
    """
    Expand bounding boxes with individual expansion values per class
    
    Args:
        bboxes_with_class: List of bounding boxes with class information
        config: ProcessingConfig with individual expansion settings
        image_shape: (height, width) of the image
        
    Returns:
        List of expanded bounding boxes (without class info)
    """
    if not config.use_individual_expansion:
        # 個別拡張が無効な場合は通常の拡張を使用
        regular_bboxes = [(x1, y1, x2, y2) for x1, y1, x2, y2, _, _ in bboxes_with_class]
        return expand_bboxes(regular_bboxes, config.bbox_expansion, image_shape)
    
    expanded_bboxes = []
    for x1, y1, x2, y2, class_name, source in bboxes_with_class:
        # クラス名に対応する個別拡張値を取得
        expansion = config.individual_expansions.get(class_name, config.bbox_expansion)
        expanded_bbox = expand_bbox((x1, y1, x2, y2), expansion, image_shape)
        expanded_bboxes.append(expanded_bbox)
        logger.debug(f"Expanded {class_name} bbox by {expansion}px: ({x1},{y1},{x2},{y2}) -> {expanded_bbox}")
    
    if bboxes_with_class:
        logger.info(f"Applied individual expansion to {len(bboxes_with_class)} bounding boxes")
    
    return expanded_bboxes

def expand_masks_radial_individual(masks: List[np.ndarray], bboxes_with_class: List[BBoxWithClass], config) -> List[np.ndarray]:
    """
    Expand multiple masks radially with individual expansion values per class
    
    Args:
        masks: List of binary masks to expand
        bboxes_with_class: List of bounding boxes with class information (same order as masks)
        config: ProcessingConfig with individual expansion settings
        
    Returns:
        List of expanded masks
    """
    if not config.use_individual_expansion:
        # 個別拡張が無効な場合は通常の拡張を使用
        return expand_masks_radial(masks, config.bbox_expansion)
    
    if len(masks) != len(bboxes_with_class):
        logger.warning(f"Mask count ({len(masks)}) doesn't match bbox count ({len(bboxes_with_class)}), using unified expansion")
        return expand_masks_radial(masks, config.bbox_expansion)
    
    expanded_masks = []
    for i, (mask, bbox_with_class) in enumerate(zip(masks, bboxes_with_class)):
        try:
            # クラス名を取得
            class_name = bbox_with_class[4]  # (x1, y1, x2, y2, class_name, source)
            
            # クラス名に対応する個別拡張値を取得
            expansion = config.individual_expansions.get(class_name, config.bbox_expansion)
            
            # マスクを個別に拡張
            expanded_mask = expand_mask_radial(mask, expansion)
            expanded_masks.append(expanded_mask)
            
            logger.debug(f"Expanded {class_name} mask {i+1} by {expansion}px radially")
            
        except Exception as e:
            logger.warning(f"Failed to expand mask {i+1}: {str(e)}, using original")
            expanded_masks.append(mask.copy())
    
    logger.info(f"Applied individual radial expansion to {len(masks)} contour masks")
    return expanded_masks

def is_developer_mode() -> bool:
    """
    開発者モードかどうかを判定
    
    Returns:
        bool: 開発者モードの場合True
    """
    try:
        # env_configの統一された判定ロジックを使用
        from auto_mosaic.src.env_config import get_env_config
        env_config = get_env_config()
        return env_config.is_developer_mode()
        
    except Exception as e:
        logger.error(f"Error checking developer mode: {e}")
        # フォールバック: 環境変数から直接読み取り
        try:
            # .developer_modeファイルによる判定
            if os.path.exists('.developer_mode'):
                return True
                
            from dotenv import load_dotenv
            load_dotenv()
            # AUTO_MOSAIC_DEV_MODEを優先して確認
            dev_mode = os.getenv('AUTO_MOSAIC_DEV_MODE', os.getenv('DEVELOPER_MODE', 'false')).strip().lower()
            return dev_mode in ('true', '1', 'yes', 'on')
        except:
            logger.warning("Developer mode check failed, defaulting to False")
            return False

def is_distribution_mode() -> bool:
    """
    配布版モードかどうかを判定
    
    Returns:
        bool: 配布版の場合True（開発者モードでない限り常にTrue）
    """
    return not is_developer_mode()

# Global logger instance
logger = 自動モザエセLogger() 