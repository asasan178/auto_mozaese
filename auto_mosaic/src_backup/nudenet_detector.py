import numpy as np
import cv2
import time
from typing import List, Tuple, Dict, Optional
from auto_mosaic.src.utils import logger

# Type alias for bounding box with class
BBoxWithClass = Tuple[int, int, int, int, str]

class NudeNetDetector:
    """NudeNet-based NSFW detector with part mapping"""
    
    def __init__(self, device: str = "auto"):
        """
        Initialize NudeNet detector
        
        Args:
            device: Device for inference ('cpu', 'cuda', or 'auto')
        """
        self.device = device
        self.detector = None
        
        # NudeNetクラスから現在のアプリケーションの部位へのマッピング
        # anime_nsfw_v4のGUI設定項目のみに対応
        # GUI対象部位: penis, pussy, testicles, anus, nipples
        self.class_mapping = {
            # Male genitalia (男性器) - 露出している場合のみ
            'MALE_GENITALIA_EXPOSED': 'penis',
            # 'EXPOSED_GENITALIA_M': 'penis',  # 念のため無効化
            # 'MALE_GENITALIA_COVERED': 服越しは対象外
            # 'COVERED_GENITALIA_M': 服越しは対象外
            
            # Female genitalia (女性器) - 露出している場合のみ → 大陰唇として扱う
            'FEMALE_GENITALIA_EXPOSED': 'labia_majora',
            # 'EXPOSED_GENITALIA_F': 'labia_majora',  # 念のため無効化 
            # 'FEMALE_GENITALIA_COVERED': 服越しは対象外
            # 'COVERED_GENITALIA_F': 服越しは対象外
            
            # Anus (肛門のみ、お尻全体は除外) - 露出している場合のみ
            'ANUS_EXPOSED': 'anus',
            'EXPOSED_ANUS': 'anus',
            # 'ANUS_COVERED': 服越しは対象外
            # 'BUTTOCKS_EXPOSED': お尻全体なので除外
            # 'EXPOSED_BUTTOCKS': お尻全体なので除外
            
            # Nipples only (乳首のみ - 女性のみ)
            'FEMALE_NIPPLE_EXPOSED': 'nipples',
            'NIPPLE_F': 'nipples',
            # 'MALE_NIPPLE_EXPOSED': 男性の乳首は対象外
            # 'NIPPLE_M': 男性の乳首は対象外
            
            # GUIにない項目は全て除外:
            # 'FEMALE_BREAST_EXPOSED': 胸全体は除外（乳首のみ対象）
            # 'MALE_BREAST_EXPOSED': 胸全体は除外
            # 'FACE_FEMALE': 顔は対象外
            # 'FACE_MALE': 顔は対象外  
            # 'ARMPITS_EXPOSED': 脇は対象外
            # 'BELLY_EXPOSED': お腹は対象外
            # 'FEET_EXPOSED': 足は対象外
            # testicles: NudeNetには直接対応するクラスがないため anime_nsfw_v4 のみ
        }
        
        # 信頼度の閾値（NudeNetの結果をフィルタリング）
        self.confidence_threshold = 0.3
        
    def _ensure_nudenet_models(self) -> bool:
        """Ensure NudeNet models are available, download if needed"""
        import sys
        import os
        from pathlib import Path
        
        # exe化時のモデルファイル確認
        if getattr(sys, 'frozen', False):
            # 実行可能ファイルのディレクトリを取得
            if hasattr(sys, '_MEIPASS'):
                exe_dir = sys._MEIPASS
            else:
                exe_dir = os.path.dirname(sys.executable)
            
            # 必要なモデルファイルを探す
            required_models = ['detector_v2_default_checkpoint.onnx', 'classifier_model.onnx']
            found_models = []
            
            for root, dirs, files in os.walk(exe_dir):
                for file in files:
                    if file in required_models:
                        found_models.append(file)
                        logger.info(f"Found NudeNet model in exe: {file}")
            
            if len(found_models) >= 1:  # 少なくとも検出器モデルがあればOK
                return True
            else:
                logger.warning("NudeNet models not found in executable")
                return False
        else:
            # 通常の実行時：モデルの自動ダウンロードを試行
            try:
                from auto_mosaic.src.downloader import downloader
                
                # NudeNetモデルが利用可能かチェック
                if downloader.is_model_available("nudenet_models"):
                    logger.info("NudeNet models already available")
                    return True
                
                # モデルのダウンロードを試行
                logger.info("Attempting to download NudeNet models...")
                success = downloader.download_model("nudenet_models")
                
                if success:
                    logger.info("Successfully downloaded NudeNet models")
                    return True
                else:
                    logger.warning("Failed to download NudeNet models")
                    return False
                    
            except Exception as e:
                logger.warning(f"Could not download NudeNet models: {e}")
                return False
        
    def initialize(self) -> bool:
        """
        Initialize NudeNet detector
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            import sys
            import os
            
            # exe化時の特別な処理
            if getattr(sys, 'frozen', False):
                logger.info("Running in executable mode, checking NudeNet availability...")
                
                # 実行可能ファイルのディレクトリを取得
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller temporary directory
                    exe_dir = sys._MEIPASS
                else:
                    # 通常の実行可能ファイル
                    exe_dir = os.path.dirname(sys.executable)
                
                logger.info(f"Executable directory: {exe_dir}")
                
                # モデルファイルの存在確認
                model_files = [
                    'classifier_model.onnx',
                    'detector_v2_default_checkpoint.onnx',
                    'detector_v2_default_checkpoint_tf.onnx'
                ]
                
                found_models = []
                for model_file in model_files:
                    model_path = os.path.join(exe_dir, model_file)
                    if os.path.exists(model_path):
                        found_models.append(model_path)
                        logger.info(f"Found model file: {model_path}")
                
                if not found_models:
                    logger.warning("No NudeNet model files found in executable directory")
                    # モデルファイルを探す
                    for root, dirs, files in os.walk(exe_dir):
                        for file in files:
                            if file.endswith('.onnx') and 'nude' in file.lower():
                                logger.info(f"Found potential model: {os.path.join(root, file)}")
            else:
                # モデルファイルの確保を試行
                if not self._ensure_nudenet_models():
                    logger.warning("Could not ensure NudeNet models are available")
            
            from nudenet import NudeDetector
            
            # NudeNetの初期化
            logger.info("Initializing NudeNet detector...")
            
            # exe化時の特別な処理：モデルパスを明示的に指定
            if getattr(sys, 'frozen', False):
                # 実行可能ファイルのディレクトリを取得
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller temporary directory
                    exe_dir = sys._MEIPASS
                else:
                    # 通常の実行可能ファイル
                    exe_dir = os.path.dirname(sys.executable)
                
                logger.info(f"Looking for NudeNet models in: {exe_dir}")
                
                # NudeNetが期待する320n.onnxファイルを作成（detector_v2から）
                detector_model_paths = [
                    os.path.join(exe_dir, 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, '_internal', 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, 'nudenet_models', 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, '_internal', 'nudenet_models', 'detector_v2_default_checkpoint.onnx'),
                ]
                
                target_320n_paths = [
                    os.path.join(exe_dir, '320n.onnx'),
                    os.path.join(exe_dir, '_internal', '320n.onnx'),
                    os.path.join(exe_dir, 'nudenet', '320n.onnx'),
                    os.path.join(exe_dir, '_internal', 'nudenet', '320n.onnx'),
                ]
                
                source_detector_path = None
                target_320n_path = None
                
                # 利用可能な検出器モデルを探す
                for path in detector_model_paths:
                    logger.info(f"Checking detector model path: {path}")
                    if os.path.exists(path):
                        source_detector_path = path
                        logger.info(f"Found source detector model: {source_detector_path}")
                        break
                
                # 320n.onnxの配置場所を決定（ルートディレクトリに直接配置）
                if source_detector_path:
                    source_dir = os.path.dirname(source_detector_path)
                    target_320n_path = os.path.join(source_dir, '320n.onnx')
                    
                    logger.info(f"Target 320n.onnx path: {target_320n_path}")
                    
                    # ディレクトリが存在することを確認
                    try:
                        os.makedirs(source_dir, exist_ok=True)
                        logger.info(f"Ensured directory exists: {source_dir}")
                    except Exception as e:
                        logger.warning(f"Could not ensure directory exists: {e}")
                        
                    # 320n.onnxファイルが存在しない場合はコピー
                    if not os.path.exists(target_320n_path):
                        try:
                            import shutil
                            shutil.copy2(source_detector_path, target_320n_path)
                            logger.info(f"Copied detector model to 320n.onnx: {target_320n_path}")
                            
                            # コピー成功の確認
                            if os.path.exists(target_320n_path):
                                file_size = os.path.getsize(target_320n_path)
                                logger.info(f"320n.onnx file created successfully (size: {file_size} bytes)")
                            else:
                                logger.error("320n.onnx file was not created despite copy operation")
                                
                        except Exception as e:
                            logger.warning(f"Could not copy detector model: {e}")
                    else:
                        logger.info(f"320n.onnx already exists: {target_320n_path}")
                else:
                    logger.warning("No source detector model found for 320n.onnx creation")
                
                # モデルファイルを探す
                detector_model = None
                classifier_model = None
                
                # 直接的なパスをチェック
                potential_detector_paths = [
                    os.path.join(exe_dir, 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, '_internal', 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, 'nudenet_models', 'detector_v2_default_checkpoint.onnx'),
                    os.path.join(exe_dir, '_internal', 'nudenet_models', 'detector_v2_default_checkpoint.onnx')
                ]
                
                potential_classifier_paths = [
                    os.path.join(exe_dir, 'classifier_model.onnx'),
                    os.path.join(exe_dir, '_internal', 'classifier_model.onnx'),
                    os.path.join(exe_dir, 'nudenet_models', 'classifier_model.onnx'),
                    os.path.join(exe_dir, '_internal', 'nudenet_models', 'classifier_model.onnx')
                ]
                
                for path in potential_detector_paths:
                    if os.path.exists(path):
                        detector_model = path
                        logger.info(f"Found detector model at: {detector_model}")
                        break
                
                for path in potential_classifier_paths:
                    if os.path.exists(path):
                        classifier_model = path
                        logger.info(f"Found classifier model at: {classifier_model}")
                        break
                
                # 見つからない場合は全体を検索
                if not detector_model or not classifier_model:
                    logger.info("Searching for models in all subdirectories...")
                    for root, dirs, files in os.walk(exe_dir):
                        for file in files:
                            if file == 'detector_v2_default_checkpoint.onnx' and not detector_model:
                                detector_model = os.path.join(root, file)
                                logger.info(f"Found detector model: {detector_model}")
                            elif file == 'classifier_model.onnx' and not classifier_model:
                                classifier_model = os.path.join(root, file)
                                logger.info(f"Found classifier model: {classifier_model}")
                
                # モデルパスを指定してNudeDetectorを初期化
                try:
                    if detector_model:
                        # カスタムモデルパスで初期化
                        logger.info(f"Initializing NudeNet with detector model: {detector_model}")
                        
                        # 環境変数を設定してONNXランタイムの問題を回避
                        os.environ['OMP_NUM_THREADS'] = '1'
                        os.environ['ORT_LOGGING_LEVEL'] = '3'  # エラーレベルのみ
                        
                        self.detector = NudeDetector(detector_model_path=detector_model)
                        logger.info("NudeNet detector initialized with custom detector model path")
                    else:
                        # デフォルト初期化を試行
                        logger.info("No custom detector model found, trying default initialization")
                        
                        # 環境変数を設定
                        os.environ['OMP_NUM_THREADS'] = '1'
                        os.environ['ORT_LOGGING_LEVEL'] = '3'
                        
                        self.detector = NudeDetector()
                        logger.info("NudeNet detector initialized with default settings")
                        
                    # 初期化成功の確認として簡単なテストを実行
                    try:
                        # 小さなダミー画像でテスト
                        import numpy as np
                        from PIL import Image
                        
                        # 32x32の小さなテスト画像を作成
                        test_image = Image.new('RGB', (32, 32), color='white')
                        test_result = self.detector.detect(test_image)
                        logger.info(f"NudeNet test detection successful: {len(test_result)} detections")
                        
                    except Exception as test_e:
                        logger.warning(f"NudeNet test detection failed, but initialization seems OK: {test_e}")
                        
                except Exception as e:
                    logger.warning(f"Failed to initialize with custom path, trying default: {e}")
                    try:
                        # 環境変数を設定
                        os.environ['OMP_NUM_THREADS'] = '1'
                        os.environ['ORT_LOGGING_LEVEL'] = '3'
                        
                        self.detector = NudeDetector()
                        logger.info("NudeNet detector initialized with default fallback")
                        
                        # 初期化成功の確認
                        try:
                            import numpy as np
                            from PIL import Image
                            test_image = Image.new('RGB', (32, 32), color='white')
                            test_result = self.detector.detect(test_image)
                            logger.info(f"NudeNet fallback test detection successful: {len(test_result)} detections")
                        except Exception as test_e:
                            logger.warning(f"NudeNet fallback test detection failed: {test_e}")
                            
                    except Exception as e2:
                        logger.error(f"Failed to initialize NudeNet detector: {e2}")
                        return False
            else:
                # 通常の初期化
                self.detector = NudeDetector()
                logger.info("NudeNet detector initialized (development environment)")
            
            logger.info("NudeNet detector initialized successfully")
            return True
            
        except ImportError as e:
            import sys
            if getattr(sys, 'frozen', False):
                logger.error(f"NudeNet not available in executable. Import error: {e}")
                logger.error("This may be due to missing dependencies or model files in the executable.")
            else:
                logger.error("NudeNet not installed. Please install with: pip install nudenet")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize NudeNet detector: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def detect_image(self, image: np.ndarray, confidence: float = 0.25, config=None) -> Dict[str, List[BBoxWithClass]]:
        """
        Detect NSFW parts in image using NudeNet
        
        Args:
            image: Input image as numpy array (BGR format)
            confidence: Confidence threshold for detection
            config: Configuration object with user settings
            
        Returns:
            Dictionary with part names as keys and list of bounding boxes as values
        """
        if self.detector is None:
            logger.warning("NudeNet detector not initialized")
            return {}

        start_time = time.time()

        try:
            # NudeNetはRGB形式を期待するため変換
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # NudeNet検出実行
            detections = self.detector.detect(rgb_image)

            # 結果を変換（ユーザー設定も考慮）
            results = self._convert_nudenet_results(detections, confidence, config)

            inference_time = time.time() - start_time
            logger.info(f"NudeNet detection completed in {inference_time:.3f}s")

            return results

        except Exception as e:
            logger.error(f"NudeNet detection failed: {e}")
            return {}
    
    def _convert_nudenet_results(self, detections: List[Dict], confidence_threshold: float, config=None) -> Dict[str, List[BBoxWithClass]]:
        """
        Convert NudeNet detection results to our format
        
        Args:
            detections: NudeNet detection results
            confidence_threshold: Minimum confidence for detection
            config: Configuration object with user settings
            
        Returns:
            Dictionary with part names as keys and bounding boxes as values
        """
        results = {}
        
        logger.info(f"[DEBUG] NudeNet raw detections: {len(detections)} objects")
        
        for detection in detections:
            class_name = detection.get('class', '')
            score = detection.get('score', 0.0)
            box = detection.get('box', [])
            
            logger.info(f"[DEBUG] NudeNet detection: class={class_name}, score={score:.3f}, box={box}")
            
            # 信頼度フィルタリング
            if score < confidence_threshold:
                logger.info(f"[DEBUG] Filtered out {class_name} (score {score:.3f} < {confidence_threshold})")
                continue
                
            # クラスマッピング
            mapped_class = self.class_mapping.get(class_name)
            if not mapped_class:
                logger.info(f"[DEBUG] No mapping for class: {class_name}")
                continue
            
            # ユーザー設定による部位フィルタリング
            if config and not self._is_part_enabled(mapped_class, config):
                logger.info(f"[DEBUG] Part {mapped_class} disabled by user settings")
                continue
                
            logger.info(f"[DEBUG] Mapped {class_name} -> {mapped_class}")
                
            # バウンディングボックス形式変換 [x, y, w, h] -> [x1, y1, x2, y2]
            if len(box) == 4:
                x, y, w, h = box
                x1, y1, x2, y2 = x, y, x + w, y + h
                
                # 結果に追加
                if mapped_class not in results:
                    results[mapped_class] = []
                
                # ソース情報を含める（6番目の要素として'PH'フラグを追加）
                results[mapped_class].append((x1, y1, x2, y2, mapped_class, 'PH'))
                logger.info(f"[DEBUG] Added to results: {mapped_class} at ({x1}, {y1}, {x2}, {y2})")
        
        logger.info(f"[DEBUG] NudeNet final results: {results}")
        return results
    
    def _is_part_enabled(self, part_name: str, config) -> bool:
        """
        Check if a body part is enabled in user configuration
        
        Args:
            part_name: Name of the body part
            config: Configuration object
            
        Returns:
            True if part is enabled, False otherwise
        """
        # 設定がない場合はすべて有効
        if not config:
            return True
        
        # selected_modelsディクショナリを取得
        selected_models = getattr(config, 'selected_models', {})
        
        # 男性器の場合：男性器または睾丸のどちらかが有効なら使用
        if part_name == 'penis':
            penis_enabled = selected_models.get('penis', False)
            testicles_enabled = selected_models.get('testicles', False)
            return penis_enabled or testicles_enabled
        
        # 大陰唇の場合：明示的に大陰唇が選択されている場合のみ有効
        # 小陰唇のみが選択されている場合は、NudeNetのFEMALE_GENITALIA_EXPOSEDは無効にする
        if part_name == 'labia_majora':
            labia_majora_enabled = selected_models.get('labia_majora', False)
            return labia_majora_enabled
        
        # その他の部位は直接selected_modelsから取得
        return selected_models.get(part_name, False)
    
    def get_supported_parts(self) -> List[str]:
        """
        Get list of supported body parts
        
        Returns:
            List of supported part names
        """
        return list(set(self.class_mapping.values()))


class HybridDetector:
    """
    Hybrid detector that combines anime_nsfw_v4 and NudeNet results
    """
    
    def __init__(self, anime_detector=None, nudenet_detector=None):
        """
        Initialize hybrid detector
        
        Args:
            anime_detector: anime_nsfw_v4 detector instance
            nudenet_detector: NudeNet detector instance
        """
        self.anime_detector = anime_detector
        self.nudenet_detector = nudenet_detector
        
    def detect_image(self, image: np.ndarray, confidence: float = 0.25, use_anime: bool = True, use_nudenet: bool = True, config=None) -> Dict[str, List[BBoxWithClass]]:
        """
        Detect using both detectors and combine results
        
        Args:
            image: Input image
            confidence: Confidence threshold
            use_anime: Whether to use anime_nsfw_v4 detector
            use_nudenet: Whether to use NudeNet detector
            config: Configuration object with user settings
            
        Returns:
            Combined detection results
        """
        combined_results = {}
        
        # イラスト専用モデルによる検出
        if use_anime and self.anime_detector:
            try:
                anime_results = self.anime_detector.detect_image(image, confidence, config)
                combined_results = self._merge_results(combined_results, anime_results, "イラスト専用モデル")
            except Exception as e:
                logger.warning(f"イラスト専用モデル detection failed: {e}")
        
        # 実写専用モデルによる検出  
        if use_nudenet and self.nudenet_detector:
            try:
                nudenet_results = self.nudenet_detector.detect_image(image, confidence, config)
                combined_results = self._merge_results(combined_results, nudenet_results, "実写専用モデル")
            except Exception as e:
                logger.warning(f"実写専用モデル detection failed: {e}")
        
        return combined_results
    
    def _merge_results(self, existing_results: Dict, new_results: Dict, source: str) -> Dict:
        """
        Merge detection results from different sources
        
        Args:
            existing_results: Existing detection results
            new_results: New detection results to merge
            source: Source detector name for logging
            
        Returns:
            Merged results
        """
        for part_name, detections in new_results.items():
            if part_name not in existing_results:
                existing_results[part_name] = []
            
            # 重複除去（IoUベース）
            for new_detection in detections:
                is_duplicate = False
                x1, y1, x2, y2 = new_detection[:4]
                
                for existing_detection in existing_results[part_name]:
                    ex1, ey1, ex2, ey2 = existing_detection[:4]
                    
                    # IoU計算
                    iou = self._calculate_iou((x1, y1, x2, y2), (ex1, ey1, ex2, ey2))
                    
                    # IoUが0.5以上なら重複とみなす
                    if iou > 0.5:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    existing_results[part_name].append(new_detection)
        
        # ログ出力
        total_detections = sum(len(dets) for dets in new_results.values())
        if total_detections > 0:
            parts_summary = ", ".join([f"{part}:{len(dets)}" for part, dets in new_results.items() if dets])
            logger.info(f"[{source}] Detected: {parts_summary}")
        
        return existing_results
    
    def _calculate_iou(self, box1: Tuple, box2: Tuple) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes
        
        Args:
            box1: First bounding box (x1, y1, x2, y2)
            box2: Second bounding box (x1, y1, x2, y2)
            
        Returns:
            IoU value between 0 and 1
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 交差領域の計算
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)
        
        # 交差領域が存在しない場合
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        # 面積計算
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0 