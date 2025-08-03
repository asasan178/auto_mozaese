"""
YOLO-based genital detection for anime/illustration images
"""

from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import time

# 動的インポート用の遅延ローダー
from auto_mosaic.src.lazy_loader import load_numpy, load_torch, load_cv2, load_ultralytics

# 動的インポートでライブラリをロード
def _load_dependencies():
    """必要な依存関係を動的にロード"""
    global np, torch, cv2, YOLO
    
    np = load_numpy()
    torch = load_torch()
    cv2 = load_cv2()
    
    # PyTorch 2.6 compatibility: Allow loading of older model files
    import torch.serialization

    # Set default weights_only behavior to False
    try:
        torch.serialization._weights_only_pickle_default = False
    except AttributeError:
        pass

    # Global override for torch.load to force weights_only=False
    _original_torch_load = torch.load
    def _patched_torch_load(f, *args, **kwargs):
        kwargs['weights_only'] = False  # Force weights_only=False for all loads
        return _original_torch_load(f, *args, **kwargs)
    torch.load = _patched_torch_load

    # ultralytics を動的にロード
    ultralytics = load_ultralytics()
    
    # Add all necessary safe globals for ultralytics
    try:
        from ultralytics.nn.tasks import SegmentationModel, DetectionModel
        from ultralytics.nn.modules import Conv, Bottleneck, C2f, SPPF
        torch.serialization.add_safe_globals([
            SegmentationModel, DetectionModel, Conv, Bottleneck, C2f, SPPF
        ])
    except ImportError:
        pass
    except Exception:
        pass

    # Additional fallback for complete compatibility
    import warnings
    warnings.filterwarnings("ignore", message="Weights only load failed.*")
    warnings.filterwarnings("ignore", message=".*WeightsUnpickler.*")

    try:
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO
    except (ImportError, AttributeError):
        YOLO = None

# グローバル変数の初期化
np = None
torch = None
cv2 = None
YOLO = None

# 依存関係がロードされているかチェックする関数
def _ensure_dependencies_loaded():
    """依存関係がロードされていることを確認"""
    global np, torch, cv2, YOLO
    if np is None or torch is None or cv2 is None or YOLO is None:
        _load_dependencies()

from auto_mosaic.src.utils import logger, BBox, BBoxWithClass, expand_bboxes, get_recommended_device
from auto_mosaic.src.downloader import downloader

class GenitalDetector:
    """YOLO-based genital region detector"""
    
    def __init__(self, model_path: str, device: str = "auto", lite: bool = False):
        """
        Initialize detector
        
        Args:
            model_path: Path to YOLO model
            device: Device for inference ('cpu', 'cuda', or 'auto')
            lite: Whether using lite model (True = specialized genital model, False = general person model)
        """
        # 依存関係を最初にロード
        _ensure_dependencies_loaded()
        
        self.model = None
        self.device_mode = device
        self.device = get_recommended_device(device)
        self.lite = lite  # 専用モデルかどうかのフラグ
        self.load_model(model_path)
        
        # Specialized model class mapping (Anime NSFW Detection v4.0)
        self.specialized_class_mapping = {
            # Anime NSFW Detection v4.0のクラスマッピング
            # 実際のクラスIDは使用するモデル(.pt)によって異なる可能性があるため、
            # "all"モデル使用時の一般的なマッピングを仮定
            0: "male_genital",     # penis
            1: "female_genital",   # pussy/vagina  
            2: "anus",             # anus
            3: "testicles",        # testicles
            4: "nipples",          # nipples
            5: "breast"            # breast (if included)
        }
        
    def load_model(self, model_path: str):
        """Load YOLO model"""
        try:
            logger.info(f"Using {self.device.upper()} for inference")
            logger.info(f"Loading model from {model_path}")
            
            # Force PyTorch to not use weights_only mode for this specific load
            import os
            original_pytorch_weights_only = os.environ.get("PYTORCH_WEIGHTS_ONLY", None)
            os.environ["PYTORCH_WEIGHTS_ONLY"] = "false"
            
            try:
                # Initialize YOLOv8 model  
                _ensure_dependencies_loaded()
                if YOLO is None:
                    from ultralytics import YOLO as LocalYOLO
                    self.model = LocalYOLO(model_path)
                else:
                    self.model = YOLO(model_path)
            finally:
                # Restore original environment variable
                if original_pytorch_weights_only is None:
                    os.environ.pop("PYTORCH_WEIGHTS_ONLY", None)
                else:
                    os.environ["PYTORCH_WEIGHTS_ONLY"] = original_pytorch_weights_only
            
            # Move model to device
            if hasattr(self.model, 'to'):
                self.model.to(self.device)
                
            model_name = "anime_nsfw_v4" if self.lite else "genital_yolov8m"
            logger.info(f"Successfully loaded {model_name} model on {self.device}")
            
            if not self.lite:
                logger.warning("Note: Using generic demo detection model. Actual genital detection accuracy is limited.")
            else:
                logger.info("Using specialized genital detection model. High-precision body part detection available.")
                
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")
    
    def detect(self, image: Any, conf: float = 0.25, config=None) -> List[BBox]:
        """
        Detect objects in image using YOLO
        
        Args:
            image: Input image as numpy array (BGR format)
            conf: Confidence threshold (0.0 - 1.0)
            config: ProcessingConfig with part selection flags
            
        Returns:
            List of bounding boxes as (x1, y1, x2, y2) tuples for selected parts
        """
        # 依存関係を確認してからnumpy操作を実行
        _ensure_dependencies_loaded()
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        if image is None or image.size == 0:
            logger.warning("Empty or invalid image provided")
            return []
        
        try:
            # Apply image preprocessing for better detection
            processed_image = self._preprocess_for_detection(image, config)
            
            # Run YOLO inference
            results = self.model(processed_image, conf=conf, verbose=False)
            
            if not results or len(results) == 0:
                logger.debug("No objects detected")
                return []
            
            result = results[0]
            if result.boxes is None or len(result.boxes) == 0:
                logger.debug("No bounding boxes found")
                return []
            
            bboxes = []
            
            if self.lite:
                # 専用モデル: 直接部位検出
                bboxes = self._process_specialized_detection(result, config)
            else:
                # 汎用モデル: 人物検出→部位推定
                bboxes = self._process_person_detection(image, result, config)
            
            # Apply bbox expansion if specified in config
            # Note: Bbox expansion is now handled at mask level for better radial expansion
            # if config and hasattr(config, 'bbox_expansion') and config.bbox_expansion != 0:
            #     original_count = len(bboxes)
            #     bboxes = expand_bboxes(bboxes, config.bbox_expansion, image.shape[:2])
            #     if config.bbox_expansion > 0:
            #         logger.info(f"Expanded {original_count} bounding boxes by +{config.bbox_expansion}px for FANZA compliance")
            #     else:
            #         logger.info(f"Contracted {original_count} bounding boxes by {config.bbox_expansion}px")
            
            return bboxes
            
        except Exception as e:
            logger.error(f"Detection failed: {str(e)}")
            return []
    
    def _process_specialized_detection(self, result, config) -> List[BBox]:
        """専用モデルによる直接部位検出"""
        bboxes = []
        
        for box in result.boxes:
            # Get bbox coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            cls_id = int(box.cls.cpu().numpy()[0])
            confidence = float(box.conf.cpu().numpy()[0])
            
            # クラスIDを部位名にマッピング
            part_name = self.specialized_class_mapping.get(cls_id, "unknown")
            
            # 設定に基づいてフィルタリング
            if config and not self._is_part_selected(part_name, config):
                continue
                
            bboxes.append((x1, y1, x2, y2))
            logger.debug(f"{part_name} region added: ({x1}, {y1}, {x2}, {y2})")
            
        return bboxes
    
    def _process_person_detection(self, image: Any, result, config) -> List[BBox]:
        """汎用モデルによる人物検出→部位推定"""
        # 既存の実装を使用
        bboxes = []
        person_count = 0
        
        for box in result.boxes:
            cls_id = int(box.cls.cpu().numpy()[0])
            
            # Person class (class 0 in COCO)
            if cls_id == 0:
                person_count += 1
                # Get bbox coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                person_bboxes = [(x1, y1, x2, y2)]
                
                # 既存の部位推定ロジックを使用
                filtered_bboxes = self._filter_by_body_parts(image, person_bboxes, config)
                bboxes.extend(filtered_bboxes)
        
        if person_count == 0:
            logger.info("No person detected")
        else:
            logger.info(f"Extracted {len(bboxes)} region(s) from {person_count} person(s)")
            
        return bboxes
    
    def _is_part_selected(self, part_name: str, config) -> bool:
        """部位が選択されているかチェック"""
        if not config:
            return True
            
        mapping = {
            "female_genital": config.female_genital,
            "male_genital": config.male_genital,
            "anus": config.female_anal,  # アナル（男女共通）
            "testicles": config.male_testis,  # 睾丸
            "nipples": False,  # 乳首は現在対象外
            "breast": False   # 胸部は対象外
        }
        
        return mapping.get(part_name, False)
    
    def _filter_by_body_parts(self, image: Any, bboxes: List[BBox], config) -> List[BBox]:
        """
        Filter detected person boxes to focus on specific body parts
        
        Args:
            image: Input image
            bboxes: List of person bounding boxes
            config: Configuration with part selection flags
            
        Returns:
            List of filtered bounding boxes for specific body parts
        """
        if not config:
            return bboxes
        
        height, width = image.shape[:2]
        filtered_boxes = []
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            box_width = x2 - x1
            box_height = y2 - y1
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # より現実的な身体比例による部位推定
            # 頭部を除いた体幹部分を基準にする
            torso_start_y = y1 + int(box_height * 0.15)  # 頭部（約15%）を除く
            torso_height = box_height - int(box_height * 0.15)
            
            # 性器部分: 体幹の60-80%位置（へそ下から股間）
            genital_y_start = torso_start_y + int(torso_height * 0.6)
            genital_y_end = torso_start_y + int(torso_height * 0.8)
            genital_x_start = center_x - int(box_width * 0.12)  # 中央から左右12%
            genital_x_end = center_x + int(box_width * 0.12)
            
            # アナル部分: 性器よりやや後方（仮想的に少し下）
            anal_y_start = genital_y_start + int(box_height * 0.05)
            anal_y_end = genital_y_end + int(box_height * 0.05)
            anal_x_start = center_x - int(box_width * 0.08)   # より狭い範囲
            anal_x_end = center_x + int(box_width * 0.08)
            
            # 睾丸部分: 性器より少し下
            testis_y_start = genital_y_end - int(box_height * 0.03)
            testis_y_end = genital_y_end + int(box_height * 0.05)
            testis_x_start = center_x - int(box_width * 0.1)
            testis_x_end = center_x + int(box_width * 0.1)
            
            # 選択された部位に基づいてボックスを生成（重複排除）
            regions_to_add = []
            
            if config.female_genital or config.male_genital:
                genital_box = (
                    max(0, genital_x_start),
                    max(0, genital_y_start),
                    min(width, genital_x_end),
                    min(height, genital_y_end)
                )
                regions_to_add.append(("genital", genital_box))
            
            if config.female_anal:
                anal_box = (
                    max(0, anal_x_start),
                    max(0, anal_y_start),
                    min(width, anal_x_end),
                    min(height, anal_y_end)
                )
                regions_to_add.append(("anal", anal_box))
            
            if config.male_testis:
                testis_box = (
                    max(0, testis_x_start),
                    max(0, testis_y_start),
                    min(width, testis_x_end),
                    min(height, testis_y_end)
                )
                regions_to_add.append(("testis", testis_box))
            
            # 重複する領域をマージして追加
            for region_name, region_box in regions_to_add:
                filtered_boxes.append(region_box)
                logger.debug(f"{region_name} region added: {region_box}")
        
        logger.info(f"人物{len(bboxes)}体から{len(filtered_boxes)}個の部位領域を抽出")
        return filtered_boxes
    
    def _preprocess_for_detection(self, image: Any, config=None) -> Any:
        """
        Return original image without preprocessing
        
        Args:
            image: Input image as numpy array (BGR format)
            config: ProcessingConfig (not used)
            
        Returns:
            Original image unchanged
        """
        return image
    
    def detect_batch(self, images: List[Any], conf: float = 0.25, config=None) -> List[List[BBox]]:
        """
        Detect genital regions in multiple images
        
        Args:
            images: List of images as numpy arrays
            conf: Confidence threshold
            config: ProcessingConfig with part selection flags
            
        Returns:
            List of bounding box lists for each image
        """
        results = []
        for i, image in enumerate(images):
            try:
                bboxes = self.detect(image, conf, config)
                results.append(bboxes)
                logger.debug(f"Processed image {i+1}/{len(images)}: {len(bboxes)} detections")
            except Exception as e:
                logger.error(f"Failed to process image {i+1}: {str(e)}")
                results.append([])
        
        return results
    
    def visualize_detections(self, image: Any, bboxes_with_class: List[BBoxWithClass]) -> Any:
        """
        Visualize detection results with colored bounding boxes
        
        Args:
            image: Original image
            bboxes_with_class: List of bounding boxes with class information
            
        Returns:
            Image with bounding boxes drawn
        """
        if not bboxes_with_class:
            return image.copy()
        
        vis_image = image.copy()
        
        # Define colors for each model class
        colors = {
            'penis': (0, 0, 255),           # Red
            'labia_minora': (255, 0, 255),  # Magenta - 小陰唇
            'labia_majora': (255, 100, 255), # Light Magenta - 大陰唇
            'pussy': (255, 0, 255),         # Magenta - 互換性維持
            'testicles': (0, 255, 255),     # Cyan
            'anus': (0, 165, 255),          # Orange
            'nipples': (255, 255, 0),       # Yellow
            'x-ray': (128, 0, 128),         # Purple
            'cross-section': (0, 128, 255), # Orange-red
            'all': (255, 0, 0)              # Blue
        }
        
        for bbox_with_class in bboxes_with_class:
            x1, y1, x2, y2, class_name, source = bbox_with_class
            
            # Get color for this class
            color = colors.get(class_name, (0, 255, 0))  # Default green
            
            # Draw bounding box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            
            # Draw class label with source information
            label = f"{class_name} ({source})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(vis_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(vis_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return vis_image
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_type": "anime_nsfw_v4" if self.lite else "genital_yolov8m",
            "device": self.device,
            "lite_mode": self.lite,
            "loaded": self.model is not None
        }
    
    def switch_model(self, use_lite: bool):
        """Switch between lite and full model"""
        if use_lite != self.lite:
            logger.info(f"Switching to {'lite' if use_lite else 'full'} model")
            self.lite = use_lite
            self.load_model(self.model.model.path)

# Factory function for easy instantiation
def create_detector(model_path: str, device: str = "auto", lite: bool = False) -> GenitalDetector:
    """
    Create and return a configured GenitalDetector instance
    
    Args:
        model_path: Path to YOLO model
        device: Device for inference ('cpu', 'cuda', or 'auto')
        lite: Whether using the lite model
        
    Returns:
        Configured GenitalDetector instance
    """
    return GenitalDetector(model_path, device, lite)

class MultiModelDetector:
    """Multiple specialized model detector for Anime NSFW Detection v4.0 with NudeNet integration"""
    
    def __init__(self, config, device: str = "auto"):
        """
        Initialize multi-model detector
        
        Args:
            config: ProcessingConfig with selected_models dictionary
            device: Device for inference ('cpu', 'cuda', or 'auto')
        """
        self.config = config
        self.device_mode = device
        self.device = get_recommended_device(device)
        self.models = {}  # Dictionary to hold loaded models
        
        # Initialize NudeNet detector
        self.nudenet_detector = None
        self.hybrid_detector = None
        
        self.load_selected_models()
        self._initialize_nudenet()
        self._setup_hybrid_detector()
        
    def load_selected_models(self):
        """Load only the selected model files"""
        from auto_mosaic.src.downloader import downloader
        
        logger.info(f"Using {self.device.upper()} for inference")
        
        # イラスト専用モデルで有効なモデルのリスト
        valid_anime_models = ["penis", "labia_minora", "pussy", "testicles", "anus", "nipples", "x-ray", "cross-section", "all"]
        
        selected_count = 0
        
        # 標準モデルの読み込み
        for model_key, is_selected in self.config.selected_models.items():
            if is_selected:
                # イラスト専用モデルでサポートされていないモデルはスキップ
                if model_key not in valid_anime_models:
                    logger.info(f"Skipping {model_key} model (not supported by イラスト専用モデル)")
                    continue
                    
                model_path = downloader.get_model_path("anime_nsfw_v4", model_key)
                if model_path and model_path.exists():
                    try:
                        logger.info(f"Loading {model_key} model from {model_path}")
                        
                        # Force PyTorch to not use weights_only mode for this specific load
                        import os
                        original_pytorch_weights_only = os.environ.get("PYTORCH_WEIGHTS_ONLY", None)
                        os.environ["PYTORCH_WEIGHTS_ONLY"] = "false"
                        
                        try:
                            # 依存関係を確認してからYOLOを使用
                            _ensure_dependencies_loaded()
                            if YOLO is None:
                                from ultralytics import YOLO as LocalYOLO
                                model = LocalYOLO(str(model_path))
                            else:
                                model = YOLO(str(model_path))
                        finally:
                            # Restore original environment variable
                            if original_pytorch_weights_only is None:
                                os.environ.pop("PYTORCH_WEIGHTS_ONLY", None)
                            else:
                                os.environ["PYTORCH_WEIGHTS_ONLY"] = original_pytorch_weights_only
                        
                        # Move model to device
                        if hasattr(model, 'to'):
                            model.to(self.device)
                            
                        self.models[model_key] = model
                        selected_count += 1
                        logger.info(f"Successfully loaded {model_key} model")
                        
                    except Exception as e:
                        logger.error(f"Failed to load {model_key} model: {str(e)}")
                else:
                    logger.warning(f"Model file not found for {model_key}: {model_path}")
        
        # カスタムモデルの読み込み
        if hasattr(self.config, 'use_custom_models') and self.config.use_custom_models:
            selected_count += self._load_custom_models()
        
        if selected_count == 0:
            # より親切なエラーメッセージを提供
            models_dir = Path(downloader.models_dir)
            anime_nsfw_dir = models_dir / "anime_nsfw_v4"
            
            error_msg = (
                "❌ 検出用モデルファイルが見つかりません。\n\n"
                f"【必要なファイル】\n"
                f"・Anime NSFW Detection v4.0 モデルファイル\n"
                f"・配置先: {anime_nsfw_dir}\n\n"
                f"【解決方法】\n"
                f"1. CivitAIから「Anime NSFW Detection v4.0」をダウンロード\n"
                f"2. ZIPファイルを展開して上記フォルダに配置\n"
                f"3. アプリケーションを再起動\n\n"
                f"【カスタムモデル】\n"
                f"または、設定 > カスタムモデル から任意の.ptファイルを指定\n\n"
                f"【フォルダを開く】\n"
                f"設定 > モデル管理 > フォルダを開く から配置先を確認できます。"
            )
            
            logger.error("No valid detection models found")
            logger.info(f"Models directory: {models_dir}")
            logger.info(f"Expected anime_nsfw_v4 directory: {anime_nsfw_dir}")
            logger.info(f"Directory exists: {anime_nsfw_dir.exists()}")
            
            if anime_nsfw_dir.exists():
                files = list(anime_nsfw_dir.glob("*.pt"))
                logger.info(f"Found .pt files: {len(files)}")
                for file in files:
                    logger.info(f"  - {file.name}")
            
            raise RuntimeError(error_msg)
            
        logger.info(f"Loaded {selected_count} specialized NSFW detection models. High-precision part detection available.")
        
    def _load_custom_models(self):
        """カスタムモデルを読み込む"""
        if not hasattr(self.config, 'custom_models'):
            return 0
            
        loaded_count = 0
        for model_name, model_config in self.config.custom_models.items():
            if not model_config.get('enabled', False):
                continue
                
            model_path = Path(model_config.get('path', ''))
            if not model_path.exists():
                logger.warning(f"Custom model file not found: {model_path}")
                continue
                
            try:
                logger.info(f"Loading custom model '{model_name}' from {model_path}")
                
                # Force PyTorch to not use weights_only mode for this specific load
                import os
                original_pytorch_weights_only = os.environ.get("PYTORCH_WEIGHTS_ONLY", None)
                os.environ["PYTORCH_WEIGHTS_ONLY"] = "false"
                
                try:
                    # 依存関係を確認してからYOLOを使用
                    _ensure_dependencies_loaded()
                    if YOLO is None:
                        from ultralytics import YOLO as LocalYOLO
                        model = LocalYOLO(str(model_path))
                    else:
                        model = YOLO(str(model_path))
                finally:
                    # Restore original environment variable
                    if original_pytorch_weights_only is None:
                        os.environ.pop("PYTORCH_WEIGHTS_ONLY", None)
                    else:
                        os.environ["PYTORCH_WEIGHTS_ONLY"] = original_pytorch_weights_only
                
                # Move model to device
                if hasattr(model, 'to'):
                    model.to(self.device)
                    
                # カスタムモデル用のキーで保存
                custom_key = f"custom_{model_name}"
                self.models[custom_key] = model
                
                # クラスマッピングを保存
                class_mapping = model_config.get('class_mapping', {})
                if class_mapping:
                    self.custom_class_mappings = getattr(self, 'custom_class_mappings', {})
                    self.custom_class_mappings[custom_key] = class_mapping
                
                loaded_count += 1
                logger.info(f"Successfully loaded custom model '{model_name}'")
                
            except Exception as e:
                logger.error(f"Failed to load custom model '{model_name}': {str(e)}")
        
        return loaded_count
    
    def _initialize_nudenet(self):
        """Initialize NudeNet detector if enabled"""
        logger.info(f"[DEBUG] Checking NudeNet initialization - config has use_nudenet: {hasattr(self.config, 'use_nudenet')}")
        if hasattr(self.config, 'use_nudenet'):
            logger.info(f"[DEBUG] use_nudenet value: {self.config.use_nudenet}")
        
        if hasattr(self.config, 'use_nudenet') and self.config.use_nudenet:
            logger.info("[DEBUG] Attempting to initialize 実写専用モデル...")
            try:
                from auto_mosaic.src.nudenet_detector import NudeNetDetector
                self.nudenet_detector = NudeNetDetector(device=self.device_mode)
                if self.nudenet_detector.initialize():
                    logger.info("✅ 実写専用モデル initialized and ready")
                else:
                    self.nudenet_detector = None
                    logger.warning("❌ Failed to initialize 実写専用モデル")
            except ImportError as e:
                import sys
                if getattr(sys, 'frozen', False):
                    logger.warning(f"❌ 実写専用モデル not available in executable version. Import error: {e}")
                    logger.warning("NudeNet requires additional DLL setup for executable version.")
                    logger.info("🔄 Application will continue with anime-only detection models")
                else:
                    logger.warning("❌ 実写専用モデル not available. Please install with: pip install nudenet")
                self.nudenet_detector = None
            except Exception as e:
                import sys
                if getattr(sys, 'frozen', False) and "DLL" in str(e):
                    logger.warning(f"❌ NudeNet DLL initialization failed in executable: {e}")
                    logger.info("🔄 This is expected in some exe environments - continuing with anime models only")
                else:
                    logger.error(f"❌ Error initializing 実写専用モデル: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                self.nudenet_detector = None
        else:
            logger.info("[DEBUG] 実写専用モデル initialization skipped (not enabled in config)")
    
    def _setup_hybrid_detector(self):
        """Setup hybrid detector that combines イラスト専用モデル and 実写専用モデル"""
        logger.info(f"[DEBUG] Setting up hybrid detector - anime_models: {len(self.models)}, nudenet: {self.nudenet_detector is not None}")
        try:
            from auto_mosaic.src.nudenet_detector import HybridDetector
            self.hybrid_detector = HybridDetector(
                anime_detector=self if self.models else None,
                nudenet_detector=self.nudenet_detector
            )
            logger.info("✅ Hybrid detector setup complete")
        except Exception as e:
            logger.error(f"❌ Failed to setup hybrid detector: {e}")
            self.hybrid_detector = None
    
    def detect(self, image: Any, conf: float = 0.25, config=None) -> List[BBoxWithClass]:
        """
        Detect objects using multiple specialized models and/or NudeNet
        
        Args:
            image: Input image as numpy array (BGR format)
            conf: Confidence threshold (0.0 - 1.0)
            config: ProcessingConfig with detection settings
            
        Returns:
            List of bounding boxes with class information from all selected detectors
        """
        if image is None or image.size == 0:
            logger.warning("Empty or invalid image provided")
            return []
        
        # Get detector settings from config
        use_anime = getattr(config, 'use_anime_detector', True) if config else True
        use_nudenet = getattr(config, 'use_nudenet', True) if config else False
        
        # Use hybrid detector if available
        if self.hybrid_detector:
            logger.info(f"Using hybrid detector: イラスト専用モデル={use_anime}, 実写専用モデル={use_nudenet}")
            return self._detect_with_hybrid(image, conf, use_anime, use_nudenet, config)
        
        # Fall back to original anime_nsfw_v4 only detection
        if use_anime and self.models:
            logger.info("Falling back to イラスト専用モデル only detection (hybrid detector not available)")
            return self._detect_anime_only(image, conf, config)
        
        logger.warning("No detectors available")
        return []
    
    def _detect_with_hybrid(self, image: Any, conf: float, use_anime: bool, use_nudenet: bool, config=None) -> List[BBoxWithClass]:
        """Use hybrid detector for combined detection"""
        try:
            combined_results = self.hybrid_detector.detect_image(
                image, 
                confidence=conf, 
                use_anime=use_anime, 
                use_nudenet=use_nudenet,
                config=config
            )
            
            # Convert to BBoxWithClass format
            all_bboxes_with_class = []
            for part_name, detections in combined_results.items():
                for detection in detections:
                    x1, y1, x2, y2, class_name, source = detection
                    all_bboxes_with_class.append((x1, y1, x2, y2, class_name, source))
            
            total_detections = len(all_bboxes_with_class)
            if total_detections > 0:
                parts_summary = ", ".join([f"{part}:{len(dets)} regions" for part, dets in combined_results.items() if dets])
                logger.info(f"[Hybrid Detection] Total: {total_detections} regions ({parts_summary})")
            else:
                logger.info("[Hybrid Detection] No target regions detected")
            
            return all_bboxes_with_class
            
        except Exception as e:
            logger.error(f"Hybrid detection failed: {e}")
            return []
    
    def _detect_anime_only(self, image: Any, conf: float, config=None) -> List[BBoxWithClass]:
        """Original イラスト専用モデル only detection"""
        if not self.models:
            logger.warning("No イラスト専用モデル loaded")
            return []
        
        all_bboxes_with_class = []
        detected_parts = {}
        detection_times = {}
        
        try:
            total_detect_start = time.time()
            
            # Run inference with each selected model
            for model_key, model in self.models.items():
                # カスタムモデルの場合の処理
                if model_key.startswith("custom_"):
                    if config and hasattr(config, 'use_custom_models') and not config.use_custom_models:
                        logger.info(f"Skipping {model_key} model (custom models disabled)")
                        continue
                    # カスタムモデルは常に有効として扱う（個別の無効化は設定レベルで管理）
                else:
                    # 標準モデルのユーザー選択をチェック
                    if config and hasattr(config, 'selected_models'):
                        if not config.selected_models.get(model_key, False):
                            logger.info(f"Skipping {model_key} model (not selected by user)")
                            continue
                
                model_start = time.time()
                
                results = model(image, conf=conf, verbose=False)
                
                model_time = time.time() - model_start
                detection_times[model_key] = model_time
                logger.info(f"  [{model_key} Model] Inference time: {model_time:.2f}s")
                
                if results and len(results) > 0:
                    result = results[0]
                    if result.boxes is not None and len(result.boxes) > 0:
                        model_bboxes = []
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                            confidence = float(box.conf.cpu().numpy()[0])
                            
                            # カスタムモデルの場合はクラス情報をマッピング
                            if model_key.startswith("custom_"):
                                class_id = int(box.cls.cpu().numpy()[0])
                                custom_class_mappings = getattr(self, 'custom_class_mappings', {})
                                class_mapping = custom_class_mappings.get(model_key, {})
                                class_name = class_mapping.get(class_id, f"class_{class_id}")
                                source = 'CU'  # Custom model source
                            else:
                                class_name = model_key
                                source = 'IL'  # Illustration model source
                            
                            # クラス情報とソース情報を追加してBBoxWithClassとして保存
                            bbox_with_class = (x1, y1, x2, y2, class_name, source)
                            all_bboxes_with_class.append(bbox_with_class)
                            model_bboxes.append((x1, y1, x2, y2))
                            logger.debug(f"{model_key} region added: ({x1}, {y1}, {x2}, {y2}) [conf: {confidence:.3f}, class: {class_name}]")
                        
                        detected_parts[model_key] = len(model_bboxes)
            
            total_detect_time = time.time() - total_detect_start
            
            # Log output
            times_str = ", ".join([f"{k}:{v:.1f}s" for k, v in detection_times.items()])
            logger.info(f"[All Models Detection] Time: {total_detect_time:.2f}s ({times_str})")
            
            if detected_parts:
                parts_str = ", ".join([f"{k}:{v} regions" for k, v in detected_parts.items()])
                logger.info(f"Detected parts: {parts_str} (total: {len(all_bboxes_with_class)} regions)")
            else:
                logger.info("No target regions detected")
            
            return all_bboxes_with_class
            
        except Exception as e:
            logger.error(f"Multi-model detection failed: {str(e)}")
            return []
    
    def detect_image(self, image: Any, confidence: float = 0.25, config=None) -> Dict[str, List]:
        """
        Wrapper method for compatibility with hybrid detector interface
        
        Args:
            image: Input image
            confidence: Confidence threshold
            config: Configuration object with user settings
            
        Returns:
            Dictionary with part names as keys and bounding boxes as values
        """
        bboxes = self._detect_anime_only(image, confidence, config)
        
        # Convert to dictionary format
        results = {}
        for bbox in bboxes:
            x1, y1, x2, y2, class_name, source = bbox
            if class_name not in results:
                results[class_name] = []
            results[class_name].append((x1, y1, x2, y2, class_name, source))
        
        return results
    
    def get_model_info(self) -> dict:
        """Get information about loaded models"""
        return {
            "model_type": "anime_nsfw_v4_multi",
            "device": self.device,
            "loaded_models": list(self.models.keys()),
            "model_count": len(self.models)
        }
    
    def visualize_detections(self, image: Any, bboxes_with_class: List[BBoxWithClass]) -> Any:
        """
        Visualize detection results with colored bounding boxes
        
        Args:
            image: Original image
            bboxes_with_class: List of bounding boxes with class information
            
        Returns:
            Image with bounding boxes drawn
        """
        if not bboxes_with_class:
            return image.copy()
        
        vis_image = image.copy()
        
        # Define colors for each model class (both anime_nsfw_v4 and NudeNet)
        colors = {
            # anime_nsfw_v4 colors
            'penis': (0, 0, 255),           # Red
            'labia_minora': (255, 0, 255),  # Magenta - 小陰唇
            'labia_majora': (255, 100, 255), # Light Magenta - 大陰唇
            'pussy': (255, 0, 255),         # Magenta - 互換性維持
            'testicles': (0, 255, 255),     # Cyan
            'anus': (0, 165, 255),          # Orange
            'nipples': (255, 255, 0),       # Yellow
            'x-ray': (128, 0, 128),         # Purple
            'cross-section': (0, 128, 255), # Orange-red
            'all': (255, 0, 0),             # Blue
            
            # NudeNet colors (different shades for distinction)
            'male_genital': (0, 0, 200),      # Dark Red
            'female_genital': (200, 0, 200),  # Dark Magenta
            'buttocks': (0, 200, 200),        # Dark Cyan
            'female_breast': (200, 200, 0),   # Dark Yellow
            'male_breast': (150, 150, 0),     # Olive
            'belly': (100, 100, 255),         # Light Blue
            'feet': (255, 100, 100),          # Light Red
            'armpits': (100, 255, 100),       # Light Green
            'face': (255, 200, 100),          # Light Orange
        }
        
        for bbox_with_class in bboxes_with_class:
            x1, y1, x2, y2, class_name, source = bbox_with_class
            
            # Get color for this class
            color = colors.get(class_name, (0, 255, 0))  # Default green
            
            # Draw bounding box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            
            # Draw class label with source indicator
            label = f"{class_name} ({source})"
                
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(vis_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(vis_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return vis_image 