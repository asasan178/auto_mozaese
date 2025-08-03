"""
Pixel mosaic application with feathered blending
"""

from typing import List, Tuple, Optional
import numpy as np
import cv2
from auto_mosaic.src.utils import logger, calculate_tile_size

class MosaicProcessor:
    """Process images with various mosaic effects"""
    
    def __init__(self):
        """Initialize mosaic processor"""
        pass
    
    def apply(self, image: np.ndarray, masks: List[np.ndarray], 
              feather: int = 5, strength: float = 1.0, config=None, 
              mosaic_type: str = "block") -> np.ndarray:
        """
        Apply mosaic effect to image using masks with FANZA-compliant settings
        
        Args:
            image: Input image in BGR format
            masks: List of binary masks (255=mosaic, 0=original)
            feather: Feather radius for soft edges (0-20)
            strength: Mosaic strength multiplier (0.5-3.0)
            config: Configuration object (for compatibility)
            mosaic_type: Type of mosaic ("block", "gaussian", "white", "black")
            
        Returns:
            Image with mosaic applied to masked regions
        """
        import time
        
        if not masks:
            logger.debug("No masks provided, returning original image")
            return image.copy()
        
        mosaic_start = time.time()
        
        height, width = image.shape[:2]
        
        # Calculate FANZA-compliant tile size or use direct settings
        if config and hasattr(config, 'use_fanza_standard'):
            use_fanza = config.use_fanza_standard
            manual_size = getattr(config, 'manual_tile_size', 16)
            # ガウスモザイクの場合は専用設定を使用
            if mosaic_type == "gaussian" and hasattr(config, 'gaussian_blur_radius'):
                if use_fanza:
                    # FANZA基準でガウス用の計算
                    tile_size = calculate_tile_size(image.shape[:2], strength, use_fanza, manual_size, mosaic_type)
                else:
                    # 直接指定のぼかし半径を使用
                    tile_size = config.gaussian_blur_radius
            else:
                tile_size = calculate_tile_size(image.shape[:2], strength, use_fanza, manual_size, mosaic_type)
        else:
            # Default to FANZA standard for backward compatibility
            use_fanza = True
            manual_size = 16
            tile_size = calculate_tile_size(image.shape[:2], strength, use_fanza, manual_size, mosaic_type)
        
        if use_fanza:
            logger.info(f"Image size: {width}x{height}, long side: {max(width, height)}")
            if mosaic_type == "gaussian":
                logger.info(f"FANZA compliant gaussian blur radius: {tile_size}px (strength: {strength})")
            elif mosaic_type in ["white", "black"]:
                logger.info(f"FANZA compliant {mosaic_type} fill (strength: {strength})")
            else:
                logger.info(f"FANZA compliant mosaic tile: {tile_size}px (strength: {strength})")
        else:
            logger.info(f"Image size: {width}x{height}")
            if mosaic_type == "gaussian":
                logger.info(f"Manual gaussian blur radius: {tile_size}px (custom setting)")
            elif mosaic_type in ["white", "black"]:
                logger.info(f"Manual {mosaic_type} fill (custom setting)")
            else:
                logger.info(f"Manual mosaic tile: {tile_size}px (custom setting)")
        
        # Apply radial expansion to masks based on processing mode
        processed_masks = masks
        processing_mode = getattr(config, 'mode', 'unknown') if config else 'unknown'
        
        if config and hasattr(config, 'bbox_expansion') and config.bbox_expansion != 0:
            if processing_mode == 'contour':
                # 輪郭モード: 輪郭の重心から放射線状に拡張
                expansion_start = time.time()
                
                if hasattr(config, 'use_individual_expansion') and config.use_individual_expansion:
                    # 個別拡張: クラス情報を使用して個別に拡張
                    if hasattr(config, 'bboxes_with_class'):
                        from auto_mosaic.src.utils import expand_masks_radial_individual
                        processed_masks = expand_masks_radial_individual(masks, config.bboxes_with_class, config)
                        logger.info(f"[Individual Contour Expansion] Applied individual expansion to {len(masks)} contour masks")
                    else:
                        # クラス情報がない場合は一律拡張
                        from auto_mosaic.src.utils import expand_masks_radial
                        processed_masks = expand_masks_radial(masks, config.bbox_expansion)
                        logger.warning(f"[Individual Expansion] Missing class info, used unified expansion: {config.bbox_expansion:+d}px")
                else:
                    # 一律拡張
                    from auto_mosaic.src.utils import expand_masks_radial
                    processed_masks = expand_masks_radial(masks, config.bbox_expansion)
                
                expansion_time = time.time() - expansion_start
                if config.bbox_expansion > 0:
                    logger.info(f"[Contour Radial Expansion] Applied +{config.bbox_expansion}px expansion to {len(masks)} contour masks in {expansion_time:.2f}s")
                else:
                    logger.info(f"[Contour Radial Contraction] Applied {config.bbox_expansion}px contraction to {len(masks)} contour masks in {expansion_time:.2f}s")
            elif processing_mode == 'rectangle':
                # 矩形モード: 拡張は既に適用済みなので何もしない
                processed_masks = masks
                logger.info(f"[Rectangle Mode] Using pre-expanded rectangular masks (no additional expansion)")
            else:
                # 不明なモード: 従来通りの拡張を適用（後方互換性のため）
                from auto_mosaic.src.utils import expand_masks_radial
                expansion_start = time.time()
                processed_masks = expand_masks_radial(masks, config.bbox_expansion)
                expansion_time = time.time() - expansion_start
                logger.warning(f"[Unknown Mode] Applied legacy expansion to {len(masks)} masks in {expansion_time:.2f}s")
        else:
            # 拡張設定なし、またはconfig未指定
            processed_masks = masks
            if processing_mode != 'unknown':
                logger.info(f"[{processing_mode.title()} Mode] No expansion specified, using original masks")
        
        # 新しい統合処理方式を使用
        result = self._apply_merged_masks(image, processed_masks, tile_size, feather, mosaic_type)
        
        total_mosaic_time = time.time() - mosaic_start
        logger.info(f"[Mosaic Total] Processing time: {total_mosaic_time:.2f}s")
        
        return result
    
    def _apply_merged_masks(self, image: np.ndarray, masks: List[np.ndarray], 
                           tile_size: int, feather: int, mosaic_type: str = "block") -> np.ndarray:
        """
        Apply mosaic using merged masks to eliminate boundary artifacts
        
        Args:
            image: Input image
            masks: List of binary masks
            tile_size: Mosaic tile size or blur radius (for gaussian)
            feather: Feather radius
            mosaic_type: Type of mosaic effect
            
        Returns:
            Image with seamless mosaic applied
        """
        import time
        
        merge_start = time.time()
        
        # Step 1: マスクを統合（重複領域を自然に融合）
        merged_mask = self._merge_overlapping_masks(masks, feather)
        
        if merged_mask is None or np.sum(merged_mask) == 0:
            logger.debug("No valid merged mask, returning original image")
            return image.copy()
        
        merge_time = time.time() - merge_start
        logger.info(f"  [Mask Merge] Time: {merge_time:.2f}s")
        
        # Step 2: 統合マスクの境界を取得
        coords = np.where(merged_mask > 0.01)  # 微小値も含める
        if len(coords[0]) == 0:
            return image.copy()
        
        y_min, y_max = coords[0].min(), coords[0].max() + 1
        x_min, x_max = coords[1].min(), coords[1].max() + 1
        
        # パディングを追加して滑らかな境界を確保
        pad = max(1, feather)
        y_min = max(0, y_min - pad)
        y_max = min(image.shape[0], y_max + pad)
        x_min = max(0, x_min - pad)
        x_max = min(image.shape[1], x_max + pad)
        
        # Step 3: 領域を抽出して処理
        region = image[y_min:y_max, x_min:x_max].copy()
        region_mask = merged_mask[y_min:y_max, x_min:x_max]
        
        if region.size == 0:
            return image.copy()
        
        # Step 4: 指定されたタイプのモザイク処理を適用
        mosaic_region = self._apply_mosaic_effect(region, tile_size, mosaic_type)
        
        # Step 5: アルファブレンディングで自然な境界を作成
        if len(region_mask.shape) == 2:
            region_mask = np.stack([region_mask] * 3, axis=2)
        
        blended_region = (region_mask * mosaic_region + 
                         (1 - region_mask) * region).astype(np.uint8)
        
        # Step 6: 結果を元画像に反映
        result = image.copy()
        result[y_min:y_max, x_min:x_max] = blended_region
        
        logger.info(f"  [Unified Mosaic] Size: {x_max-x_min}x{y_max-y_min}, seamless processing ({mosaic_type})")
        
        return result
    
    def _apply_mosaic_effect(self, image: np.ndarray, tile_size: int, mosaic_type: str) -> np.ndarray:
        """
        Apply specified mosaic effect to image region
        
        Args:
            image: Input image region
            tile_size: Size parameter (tile size for block, blur radius for gaussian)
            mosaic_type: Type of effect ("block", "gaussian", "white", "black")
            
        Returns:
            Processed image with mosaic effect applied
        """
        if mosaic_type == "block":
            return self._pixelate_region(image, tile_size)
        elif mosaic_type == "gaussian":
            return self._gaussian_blur_region(image, tile_size)
        elif mosaic_type == "white":
            return self._solid_fill_region(image, (255, 255, 255))
        elif mosaic_type == "black":
            return self._solid_fill_region(image, (0, 0, 0))
        else:
            logger.warning(f"Unknown mosaic type '{mosaic_type}', using block mosaic")
            return self._pixelate_region(image, tile_size)
    
    def _gaussian_blur_region(self, image: np.ndarray, blur_radius: int) -> np.ndarray:
        """
        Apply Gaussian blur to image region
        
        Args:
            image: Input image region
            blur_radius: Blur radius (derived from FANZA tile size)
            
        Returns:
            Blurred image
        """
        if blur_radius <= 1:
            return image
        
        # カーネルサイズは奇数である必要がある
        kernel_size = blur_radius * 2 + 1
        
        # ガウシアンブラーを適用
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), blur_radius)
        
        return blurred
    
    def _solid_fill_region(self, image: np.ndarray, color: Tuple[int, int, int]) -> np.ndarray:
        """
        Fill image region with solid color
        
        Args:
            image: Input image region
            color: Fill color in BGR format (B, G, R)
            
        Returns:
            Solid color filled image
        """
        filled = np.full_like(image, color, dtype=np.uint8)
        return filled
    
    def _merge_overlapping_masks(self, masks: List[np.ndarray], feather: int) -> Optional[np.ndarray]:
        """
        Merge multiple masks with smooth transitions in overlapping areas
        
        Args:
            masks: List of binary masks
            feather: Feather radius for smooth blending
            
        Returns:
            Merged float mask (0.0-1.0) or None if no valid masks
        """
        if not masks:
            return None
        
        # 最初のマスクの形状を基準にする
        base_shape = masks[0].shape[:2]
        merged_mask = np.zeros(base_shape, dtype=np.float32)
        
        valid_mask_count = 0
        
        for i, mask in enumerate(masks):
            if mask.shape[:2] != base_shape:
                logger.warning(f"Mask {i+1} shape mismatch, skipping")
                continue
            
            # バイナリマスクを正規化
            if mask.dtype != np.float32:
                normalized_mask = mask.astype(np.float32) / 255.0
            else:
                normalized_mask = mask
            
            # フェザリング適用
            if feather > 0:
                kernel_size = max(1, feather * 2 + 1)
                feathered_mask = cv2.GaussianBlur(normalized_mask, (kernel_size, kernel_size), feather)
            else:
                feathered_mask = normalized_mask
            
            # マスクを累積（最大値ベース）
            # 重複領域では自然な最大値を取ることで境界を消す
            merged_mask = np.maximum(merged_mask, feathered_mask)
            valid_mask_count += 1
        
        if valid_mask_count == 0:
            return None
        
        # 最終的なフェザリング処理で更に滑らかに
        if feather > 0:
            final_kernel = max(1, feather // 2 * 2 + 1)
            merged_mask = cv2.GaussianBlur(merged_mask, (final_kernel, final_kernel), feather // 2)
        
        logger.info(f"  [Mask Merge] Combined {valid_mask_count} masks, max intensity: {merged_mask.max():.3f}")
        
        return merged_mask
    
    def _apply_single_mask(self, image: np.ndarray, mask: np.ndarray, 
                          tile: int, feather: int) -> np.ndarray:
        """
        Apply mosaic to a single mask region
        
        Args:
            image: Input image
            mask: Binary mask
            tile: Tile size
            feather: Feather radius
            
        Returns:
            Image with mosaic applied to masked region
        """
        if mask.shape[:2] != image.shape[:2]:
            logger.error(f"Mask shape {mask.shape[:2]} doesn't match image shape {image.shape[:2]}")
            return image
        
        # Find bounding box of the mask to optimize processing
        bbox = self._get_mask_bbox(mask)
        if bbox is None:
            logger.warning("Empty mask, skipping")
            return image
        
        x1, y1, x2, y2 = bbox
        
        # Extract region of interest
        roi_image = image[y1:y2, x1:x2].copy()
        roi_mask = mask[y1:y2, x1:x2]
        
        # Apply mosaic to ROI
        mosaic_roi = self._pixelate_region(roi_image, tile)
        
        # Create feathered mask
        if feather > 0:
            feathered_mask = self._create_feathered_mask(roi_mask, feather)
        else:
            feathered_mask = roi_mask.astype(np.float32) / 255.0
        
        # Blend mosaic with original
        blended_roi = self._blend_with_mask(roi_image, mosaic_roi, feathered_mask)
        
        # Place back into full image
        result = image.copy()
        result[y1:y2, x1:x2] = blended_roi
        
        return result
    
    def _pixelate_region(self, image: np.ndarray, tile_size: int) -> np.ndarray:
        """
        Apply pixelation (mosaic) effect to image region
        
        Args:
            image: Input image region
            tile_size: Size of mosaic tiles
            
        Returns:
            Pixelated image
        """
        if tile_size <= 1:
            return image
        
        height, width = image.shape[:2]
        
        # Downsample
        small_height = max(1, height // tile_size)
        small_width = max(1, width // tile_size)
        
        small_image = cv2.resize(image, (small_width, small_height), 
                                interpolation=cv2.INTER_LINEAR)
        
        # Upsample back to original size
        pixelated = cv2.resize(small_image, (width, height), 
                              interpolation=cv2.INTER_NEAREST)
        
        return pixelated
    
    def _create_feathered_mask(self, mask: np.ndarray, feather_radius: int) -> np.ndarray:
        """
        Create feathered (soft-edge) mask
        
        Args:
            mask: Binary mask (0/255)
            feather_radius: Gaussian blur radius
            
        Returns:
            Feathered mask (0.0-1.0 float)
        """
        if feather_radius <= 0:
            return mask.astype(np.float32) / 255.0
        
        # Convert to float
        float_mask = mask.astype(np.float32) / 255.0
        
        # Apply Gaussian blur for feathering
        kernel_size = feather_radius * 2 + 1
        feathered = cv2.GaussianBlur(float_mask, (kernel_size, kernel_size), feather_radius)
        
        return feathered
    
    def _blend_with_mask(self, original: np.ndarray, mosaic: np.ndarray, 
                        mask: np.ndarray) -> np.ndarray:
        """
        Blend original and mosaic images using alpha mask
        
        Args:
            original: Original image region
            mosaic: Mosaic image region  
            mask: Alpha mask (0.0-1.0)
            
        Returns:
            Blended image
        """
        # Ensure mask has the right dimensions
        if len(mask.shape) == 2:
            mask = mask[:, :, np.newaxis]  # Add channel dimension
        
        # Alpha blending
        blended = original * (1 - mask) + mosaic * mask
        
        return blended.astype(np.uint8)
    
    def _get_mask_bbox(self, mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Get bounding box of non-zero pixels in mask
        
        Args:
            mask: Binary mask
            
        Returns:
            (x1, y1, x2, y2) or None if mask is empty
        """
        coords = np.where(mask > 0)
        if len(coords[0]) == 0:
            return None
        
        y1, y2 = coords[0].min(), coords[0].max() + 1
        x1, x2 = coords[1].min(), coords[1].max() + 1
        
        return (x1, y1, x2, y2)
    
    def preview_mosaic(self, image: np.ndarray, masks: List[np.ndarray], 
                      tile: Optional[int] = None, feather: int = 5, 
                      strength: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate preview showing original and mosaic result side by side
        
        Args:
            image: Input image
            masks: List of masks
            tile: Tile size
            feather: Feather radius
            strength: Strength multiplier
            
        Returns:
            Tuple of (original_image, mosaic_result)
        """
        mosaic_result = self.apply(image, masks, tile, feather, strength)
        
        return image.copy(), mosaic_result
    
    def get_mosaic_stats(self, image: np.ndarray, masks: List[np.ndarray]) -> dict:
        """
        Get statistics about mosaic application
        
        Args:
            image: Input image
            masks: List of masks
            
        Returns:
            Dictionary with statistics
        """
        total_pixels = image.shape[0] * image.shape[1]
        mosaic_pixels = 0
        
        for mask in masks:
            mosaic_pixels += np.sum(mask > 0)
        
        coverage_percent = (mosaic_pixels / total_pixels) * 100
        
        return {
            "total_pixels": total_pixels,
            "mosaic_pixels": int(mosaic_pixels),
            "coverage_percent": round(coverage_percent, 2),
            "num_regions": len(masks),
            "image_size": f"{image.shape[1]}x{image.shape[0]}"
        }

# Factory function
def create_mosaic_processor() -> MosaicProcessor:
    """
    Create and return a configured MosaicProcessor instance
    
    Returns:
        Configured MosaicProcessor instance
    """
    return MosaicProcessor()

# Convenience function for direct application
def apply_mosaic(image: np.ndarray, masks: List[np.ndarray], 
                tile: Optional[int] = None, feather: int = 5, 
                strength: float = 1.0, mosaic_type: str = "block") -> np.ndarray:
    """
    Apply mosaic directly without creating processor instance
    
    Args:
        image: Input image
        masks: List of masks
        tile: Tile size (auto-calculated if None)
        feather: Feather radius
        strength: Strength multiplier
        mosaic_type: Type of mosaic effect
        
    Returns:
        Processed image
    """
    processor = create_mosaic_processor()
    return processor.apply(image, masks, feather, strength, None, mosaic_type) 