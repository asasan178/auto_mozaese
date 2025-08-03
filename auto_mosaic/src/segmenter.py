"""
SAM-based mask extraction for precise genital region segmentation
"""

from typing import List, Optional, Tuple
import numpy as np
import torch
from pathlib import Path
import time

try:
    from segment_anything import sam_model_registry, SamPredictor
except ImportError:
    sam_model_registry = None
    SamPredictor = None

from auto_mosaic.src.utils import logger, BBox, get_recommended_device
from auto_mosaic.src.downloader import downloader

class GenitalSegmenter:
    """SAM-based segmenter for precise genital region masks"""
    
    def __init__(self, model_type: str = "vit_h", device: str = "auto"):
        """
        Initialize SAM segmenter
        
        Args:
            model_type: "vit_h" for high accuracy or "vit_b" for lightweight
            device: Device for inference ('cpu', 'cuda', or 'auto')
        """
        self.predictor = None
        self.model_type = model_type
        self.device_mode = device
        self.device = get_recommended_device(device)
        self._load_model()
    
    def _get_device_info(self) -> str:
        """Get device information for logging"""
        if self.device == "cuda" and torch.cuda.is_available():
            return f"Using GPU for SAM: {torch.cuda.get_device_name()}"
        else:
            return "Using CPU for SAM inference"
    
    def _load_model(self):
        """Load SAM model with automatic download"""
        if sam_model_registry is None or SamPredictor is None:
            raise ImportError(
                "segment_anything package is required. Install with: "
                "pip install git+https://github.com/facebookresearch/segment-anything.git"
            )
        
        model_name = f"sam_{self.model_type}"
        
        # Ensure model is downloaded
        if not downloader.is_model_available(model_name):
            model_desc = "ViT-H (high accuracy)" if self.model_type == "vit_h" else "ViT-B (lightweight)"
            logger.info(f"Downloading SAM {model_desc} model...")
            success = downloader.download_model(model_name)
            if not success:
                raise RuntimeError(f"Failed to download SAM {model_desc} model")
        
        model_path = downloader.get_model_path(model_name)
        logger.info(f"Loading SAM {self.model_type.upper()} model from {model_path}")
        logger.info(self._get_device_info())
        
        try:
            # Force PyTorch to not use weights_only mode for SAM model loading
            import os
            original_pytorch_weights_only = os.environ.get("PYTORCH_WEIGHTS_ONLY", None)
            os.environ["PYTORCH_WEIGHTS_ONLY"] = "false"
            
            try:
                sam = sam_model_registry[self.model_type](checkpoint=str(model_path))
                sam.to(device=self.device)
            finally:
                # Restore original environment variable
                if original_pytorch_weights_only is None:
                    os.environ.pop("PYTORCH_WEIGHTS_ONLY", None)
                else:
                    os.environ["PYTORCH_WEIGHTS_ONLY"] = original_pytorch_weights_only
            
            self.predictor = SamPredictor(sam)
            model_desc = "ViT-H (high accuracy, 2.4GB)" if self.model_type == "vit_h" else "ViT-B (lightweight, 358MB)"
            logger.info(f"Successfully loaded SAM {model_desc} model on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load SAM model: {str(e)}")
            raise
    
    def set_image(self, image: np.ndarray):
        """
        Set image for segmentation (preprocessing step)
        
        Args:
            image: Input image in BGR format (OpenCV)
        """
        if self.predictor is None:
            raise RuntimeError("SAM model not loaded")
        
        # Convert BGR to RGB for SAM
        rgb_image = image[:, :, ::-1]  # BGR to RGB
        
        try:
            self.predictor.set_image(rgb_image)
            logger.debug("Image set for SAM processing")
        except Exception as e:
            logger.error(f"Failed to set image for SAM: {str(e)}")
            raise
    
    def masks(self, image: np.ndarray, boxes: List[BBox]) -> List[np.ndarray]:
        """
        Generate masks for bounding boxes using SAM
        
        Args:
            image: Input image in BGR format
            boxes: List of bounding boxes (x1, y1, x2, y2)
            
        Returns:
            List of binary masks (uint8, 255=foreground, 0=background)
        """
        if not boxes:
            logger.debug("No bounding boxes provided")
            return []
        
        if self.predictor is None:
            raise RuntimeError("SAM model not loaded")
        
        total_start = time.time()
        
        # Set image for SAM
        set_image_start = time.time()
        self.set_image(image)
        set_image_time = time.time() - set_image_start
        logger.info(f"  [SAM Image Setup] Time: {set_image_time:.2f}s")
        
        masks = []
        mask_times = []
        
        for i, bbox in enumerate(boxes):
            try:
                mask_start = time.time()
                mask = self._generate_mask_for_bbox(bbox)
                mask_time = time.time() - mask_start
                mask_times.append(mask_time)
                
                if mask is not None:
                    masks.append(mask)
                    logger.info(f"  [Mask {i+1} Generation] Time: {mask_time:.2f}s")
                else:
                    logger.warning(f"Failed to generate mask for bbox {i+1}")
                    
            except Exception as e:
                logger.error(f"Error generating mask for bbox {i+1}: {str(e)}")
                continue
        
        total_time = time.time() - total_start
        avg_mask_time = sum(mask_times) / len(mask_times) if mask_times else 0
        
        logger.info(f"[SAM Total] Processing time: {total_time:.2f}s (avg mask time: {avg_mask_time:.2f}s)")
        logger.info(f"Generated {len(masks)} masks from {len(boxes)} bounding boxes")
        return masks
    
    def _generate_mask_for_bbox(self, bbox: BBox) -> Optional[np.ndarray]:
        """
        Generate mask for a single bounding box
        
        Args:
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Binary mask or None if failed
        """
        x1, y1, x2, y2 = bbox
        
        # Convert bbox to SAM input format
        input_box = np.array([x1, y1, x2, y2])
        
        try:
            masks, scores, logits = self.predictor.predict(
                point_coords=None,
                point_labels=None,
                box=input_box[None, :],  # Add batch dimension
                multimask_output=False  # Single mask output
            )
            
            # Get the best mask
            if len(masks) > 0:
                mask = masks[0]  # First (and only) mask
                
                # Convert to uint8 format (255/0)
                mask_uint8 = (mask * 255).astype(np.uint8)
                
                return mask_uint8
            
        except Exception as e:
            logger.error(f"SAM prediction failed: {str(e)}")
        
        return None
    
    def refine_mask(self, image: np.ndarray, initial_mask: np.ndarray, 
                   positive_points: Optional[List[Tuple[int, int]]] = None,
                   negative_points: Optional[List[Tuple[int, int]]] = None) -> np.ndarray:
        """
        Refine existing mask using point prompts
        
        Args:
            image: Input image
            initial_mask: Initial mask to refine
            positive_points: Points that should be included
            negative_points: Points that should be excluded
            
        Returns:
            Refined mask
        """
        if self.predictor is None:
            raise RuntimeError("SAM model not loaded")
        
        self.set_image(image)
        
        # Prepare point inputs
        point_coords = []
        point_labels = []
        
        if positive_points:
            point_coords.extend(positive_points)
            point_labels.extend([1] * len(positive_points))
        
        if negative_points:
            point_coords.extend(negative_points)
            point_labels.extend([0] * len(negative_points))
        
        if not point_coords:
            logger.warning("No points provided for refinement")
            return initial_mask
        
        try:
            point_coords = np.array(point_coords)
            point_labels = np.array(point_labels)
            
            # Use initial mask as input
            mask_input = initial_mask.astype(np.float32) / 255.0
            mask_input = mask_input[None, :, :]  # Add batch dimension
            
            masks, scores, logits = self.predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                mask_input=mask_input,
                multimask_output=False
            )
            
            if len(masks) > 0:
                refined_mask = (masks[0] * 255).astype(np.uint8)
                logger.debug("Mask refined successfully")
                return refined_mask
            
        except Exception as e:
            logger.error(f"Mask refinement failed: {str(e)}")
        
        return initial_mask
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_type": f"SAM {self.model_type.upper()}",
            "device": self.device,
            "loaded": self.predictor is not None,
            "memory_usage_gb": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate GPU/CPU memory usage in GB"""
        if self.device == "cuda" and torch.cuda.is_available():
            # Get current GPU memory usage
            memory_used = torch.cuda.memory_allocated() / (1024**3)
            return round(memory_used, 2)
        else:
            # Rough estimate for CPU usage
            return 2.5  # SAM ViT-H typically uses ~2.5GB
    
    def clear_cache(self):
        """Clear GPU cache to free memory"""
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("GPU cache cleared")

# Factory function for easy instantiation
def create_segmenter(model_type: str = "vit_h") -> GenitalSegmenter:
    """
    Create and return a configured GenitalSegmenter instance
    
    Args:
        model_type: "vit_h" for high accuracy or "vit_b" for lightweight
        
    Returns:
        Configured GenitalSegmenter instance
    """
    return GenitalSegmenter(model_type=model_type) 