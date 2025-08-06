import numpy as np
import cv2
import time
from typing import List, Tuple, Dict, Optional
from auto_mosaic.src.utils import logger, expand_bbox

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
        
    def initialize(self) -> bool:
        """
        Initialize NudeNet detector
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            from nudenet import NudeDetector
            
            # NudeNetの初期化
            logger.info("Initializing NudeNet detector...")
            self.detector = NudeDetector()
            logger.info("NudeNet detector initialized successfully")
            return True
            
        except ImportError:
            logger.error("NudeNet not installed. Please install with: pip install nudenet")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize NudeNet detector: {e}")
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
            # 画像サイズを取得
            image_shape = image.shape[:2]  # (height, width)
            results = self._convert_nudenet_results(detections, confidence, config, image_shape)

            inference_time = time.time() - start_time
            logger.info(f"NudeNet detection completed in {inference_time:.3f}s")

            return results

        except Exception as e:
            logger.error(f"NudeNet detection failed: {e}")
            return {}
    
    def _convert_nudenet_results(self, detections: List[Dict], confidence_threshold: float, config=None, image_shape=None) -> Dict[str, List[BBoxWithClass]]:
        """
        Convert NudeNet detection results to our format
        
        Args:
            detections: NudeNet detection results
            confidence_threshold: Minimum confidence for detection
            config: Configuration object with user settings
            image_shape: (height, width) of the image for bbox adjustment
            
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
                
                # NudeNet専用範囲調整を適用
                if config and hasattr(config, 'use_nudenet_shrink') and config.use_nudenet_shrink and image_shape:
                    shrink_value = config.nudenet_shrink_values.get(mapped_class, 0)
                    if shrink_value != 0:
                        original_bbox = (x1, y1, x2, y2)
                        adjusted_bbox = expand_bbox(original_bbox, shrink_value, image_shape)
                        x1, y1, x2, y2 = adjusted_bbox
                        logger.info(f"[DEBUG] NudeNet range adjustment for {mapped_class}: {shrink_value:+d}px, bbox {original_bbox} -> {adjusted_bbox}")
                
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