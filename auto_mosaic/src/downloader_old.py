"""
Model file downloader with progress tracking and caching
"""

import hashlib
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Dict, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import threading
import time

from auto_mosaic.src.utils import logger, get_models_dir

class DownloadProgress:
    """Progress tracking for downloads"""
    
    def __init__(self, total_size: int, callback: Optional[Callable[[int, int], None]] = None):
        self.total_size = total_size
        self.downloaded = 0
        self.callback = callback
        self.start_time = time.time()
    
    def update(self, chunk_size: int):
        self.downloaded += chunk_size
        if self.callback:
            self.callback(self.downloaded, self.total_size)
    
    def get_progress_percent(self) -> int:
        if self.total_size == 0:
            return 0
        return int((self.downloaded / self.total_size) * 100)
    
    def get_speed_mbps(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0
        return (self.downloaded / (1024 * 1024)) / elapsed

class ModelDownloader:
    """Download and cache ML model files"""
    
    # Model configurations (updated for Anime NSFW Detection v4.0)
    MODELS = {
        "genital_yolov8m": {
            "url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8m.pt",
            "description": "YOLOv8m 中型モデル（推奨）",
            "size": "50 MB",
            "filename": "yolov8m.pt",
            "type": "single"
        },
        "yolo_lite": {
            "url": "https://civitai.com/api/download/models/1863248?type=Archive&format=Other",
            "description": "Anime NSFW Detection v4.0（CivitAI・アニメ特化・最高精度）",
            "size": "約100 MB",
            "filename": "animeNSFWDetection_v40.zip",
            "extract_dir": "anime_nsfw_v4",
            "type": "zip",
            "main_models": {
                "all": "ntd11_anime_nsfw_segm_v4_all.pt",
                "penis": "ntd11_anime_nsfw_segm_v4_penis.pt", 
                "labia_minora": "ntd11_anime_nsfw_segm_v4_pussy.pt",  # 小陰唇（anime_nsfw_v4）
                "pussy": "ntd11_anime_nsfw_segm_v4_pussy.pt",  # 互換性維持
                "testicles": "ntd11_anime_nsfw_segm_v4_testicles.pt",
                "anus": "ntd11_anime_nsfw_segm_v4_anus.pt",
                "nipples": "ntd11_anime_nsfw_segm_v4_nipples.pt",
                "x-ray": "ntd11_anime_nsfw_segm_v4_x-ray.pt",
                "cross-section": "ntd11_anime_nsfw_segm_v4_cross-section.pt"
            }
        },
        "sam_vit_h": {
            "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
            "description": "SAM ViT-H セグメンテーションモデル（高精度）",
            "size": "2.4 GB",
            "filename": "sam_vit_h.pth",
            "type": "single"
        },
        "sam_vit_b": {
            "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
            "description": "SAM ViT-B セグメンテーションモデル（軽量版）",
            "size": "358 MB",
            "filename": "sam_vit_b.pth",
            "type": "single"
        }
    }
    
    def __init__(self):
        self.models_dir = get_models_dir()
        self.download_log = self.models_dir / "download.log"
        self._log_lock = threading.Lock()
    
    def _log_download(self, message: str):
        """Log download events to file"""
        with self._log_lock:
            with open(self.download_log, "a", encoding="utf-8") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if model file exists locally"""
        if model_name not in self.MODELS:
            return False
        
        model_info = self.MODELS[model_name]
        
        if model_info.get("type") == "zip":
            # Check if extract directory exists with main models
            extract_dir = self.models_dir / model_info["extract_dir"]
            if not extract_dir.exists():
                return False
            
            # Check if at least the "all" model exists
            main_model = extract_dir / model_info["main_models"]["all"]
            return main_model.exists() and main_model.stat().st_size > 0
        else:
            # Single file model
            model_path = self.models_dir / model_info["filename"]
            return model_path.exists() and model_path.stat().st_size > 0
    
    def get_model_path(self, model_name: str, specific_model: str = "all") -> Optional[Path]:
        """Get local path to model file"""
        if not self.is_model_available(model_name):
            return None
        
        model_info = self.MODELS[model_name]
        
        if model_info.get("type") == "zip":
            extract_dir = self.models_dir / model_info["extract_dir"]
            if specific_model in model_info["main_models"]:
                return extract_dir / model_info["main_models"][specific_model]
            else:
                return extract_dir / model_info["main_models"]["all"]
        else:
            return self.models_dir / model_info["filename"]
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download model file if not already cached
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates (downloaded, total)
            
        Returns:
            True if successful, False otherwise
        """
        if model_name not in self.MODELS:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_info = self.MODELS[model_name]
        
        # Check if already downloaded
        if self.is_model_available(model_name):
            logger.info(f"Model {model_name} already available")
            return True
        
        # For zip models, check if zip file exists manually downloaded
        if model_info.get("type") == "zip":
            manual_zip = self.models_dir / model_info["filename"]
            if manual_zip.exists():
                logger.info(f"Found manually downloaded zip file: {manual_zip.name}")
                try:
                    return self._extract_existing_zip(model_info, manual_zip)
                except Exception as e:
                    logger.error(f"Failed to extract manual zip: {str(e)}")
                    # Continue to normal download
        
        logger.info(f"Downloading {model_info['description']} ({model_info['size']})...")
        self._log_download(f"Starting download: {model_name} from {model_info['url']}")
        
        try:
            if model_info.get("type") == "zip":
                return self._download_and_extract_zip(model_info, progress_callback)
            else:
                model_path = self.models_dir / model_info["filename"]
                return self._download_file(model_info["url"], model_path, progress_callback)
        except Exception as e:
            error_msg = f"Failed to download {model_name}: {str(e)}"
            logger.error(error_msg)
            self._log_download(f"ERROR: {error_msg}")
            return False
    
    def _download_and_extract_zip(self, model_info: Dict, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download and extract zip file"""
        zip_path = self.models_dir / model_info["filename"]
        extract_dir = self.models_dir / model_info["extract_dir"]
        
        try:
            # Download zip file
            success = self._download_file(model_info["url"], zip_path, progress_callback)
            if not success:
                return False
            
            # Extract zip file
            logger.info(f"Extracting {zip_path.name}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Clean up zip file
            zip_path.unlink()
            
            # Verify extracted files
            for model_key, model_file in model_info["main_models"].items():
                model_path = extract_dir / model_file
                if not model_path.exists():
                    logger.warning(f"Expected model file not found: {model_file}")
            
            logger.info(f"Successfully extracted Anime NSFW Detection v4.0 models")
            self._log_download(f"SUCCESS: Extracted {model_info['filename']}")
            
            return True
            
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid zip file")
            if zip_path.exists():
                zip_path.unlink()
            return False
        except Exception as e:
            logger.error(f"Failed to extract zip file: {str(e)}")
            if zip_path.exists():
                zip_path.unlink()
            return False
    
    def _download_file(self, url: str, target_path: Path, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download file with progress tracking"""
        
        # Create request with headers to avoid 403 errors
        request = Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        request.add_header('Accept', '*/*')
        request.add_header('Accept-Language', 'en-US,en;q=0.9,ja;q=0.8')
        request.add_header('Accept-Encoding', 'gzip, deflate, br')
        request.add_header('Connection', 'keep-alive')
        request.add_header('Upgrade-Insecure-Requests', '1')
        if 'civitai.com' in url:
            request.add_header('Referer', 'https://civitai.com/')
            request.add_header('Origin', 'https://civitai.com')
        
        try:
            with urlopen(request) as response:
                total_size = int(response.headers.get('content-length', 0))
                content_type = response.headers.get('content-type', 'unknown')
                
                # Debug logging for CivitAI downloads
                if 'civitai.com' in url:
                    logger.info(f"Response content-type: {content_type}")
                    logger.info(f"Response headers: {dict(response.headers)}")
                
                if total_size == 0:
                    logger.warning("Unable to determine file size")
                
                progress = DownloadProgress(total_size, progress_callback)
                
                # Download to temporary file first
                temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
                
                with open(temp_path, "wb") as f:
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        progress.update(len(chunk))
                
                # Move temp file to final location
                shutil.move(str(temp_path), str(target_path))
                
                # Debug: Check actual file type for CivitAI downloads
                if 'civitai.com' in url:
                    with open(target_path, 'rb') as f:
                        first_bytes = f.read(16)
                        logger.info(f"Downloaded file first 16 bytes: {first_bytes.hex()}")
                        if first_bytes.startswith(b'PK'):
                            logger.info("File appears to be a ZIP archive")
                        elif first_bytes.startswith(b'<!DOCTYPE') or first_bytes.startswith(b'<html'):
                            logger.info("File appears to be HTML (redirect page)")
                        else:
                            logger.info("File type unknown")
                
                logger.info(f"Successfully downloaded {target_path.name} ({progress.downloaded / (1024*1024):.1f} MB)")
                self._log_download(f"SUCCESS: Downloaded {target_path.name}")
                
                return True
                
        except (URLError, HTTPError) as e:
            raise Exception(f"Network error: {str(e)}")
        except OSError as e:
            raise Exception(f"File system error: {str(e)}")
    
    def _extract_existing_zip(self, model_info: Dict, zip_path: Path) -> bool:
        """Extract manually downloaded zip file"""
        extract_dir = self.models_dir / model_info["extract_dir"]
        
        try:
            logger.info(f"Extracting manually downloaded {zip_path.name}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Verify extracted files
            for model_key, model_file in model_info["main_models"].items():
                model_path = extract_dir / model_file
                if not model_path.exists():
                    logger.warning(f"Expected model file not found: {model_file}")
            
            logger.info(f"Successfully extracted manually downloaded {model_info['filename']}")
            self._log_download(f"SUCCESS: Extracted manual download {model_info['filename']}")
            
            return True
            
        except zipfile.BadZipFile:
            logger.error("Manually downloaded file is not a valid zip file")
            return False
        except Exception as e:
            logger.error(f"Failed to extract manually downloaded zip: {str(e)}")
            return False
    
    def download_all_models(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Dict[str, bool]:
        """
        Download all required models
        
        Args:
            progress_callback: Optional callback (model_name, downloaded, total)
            
        Returns:
            Dict mapping model names to success status
        """
        results = {}
        
        for model_name in self.MODELS:
            def model_progress(downloaded: int, total: int):
                if progress_callback:
                    progress_callback(model_name, downloaded, total)
            
            results[model_name] = self.download_model(model_name, model_progress)
        
        return results
    
    def verify_model_integrity(self, model_name: str, expected_sha256: Optional[str] = None) -> bool:
        """
        Verify model file integrity (optional SHA256 check)
        
        Args:
            model_name: Name of the model to verify
            expected_sha256: Expected SHA256 hash (optional)
            
        Returns:
            True if valid, False otherwise
        """
        model_path = self.get_model_path(model_name)
        if not model_path:
            return False
        
        # Basic existence and size check
        if not model_path.exists() or model_path.stat().st_size == 0:
            return False
        
        # SHA256 verification if provided
        if expected_sha256:
            with open(model_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                return file_hash.lower() == expected_sha256.lower()
        
        return True

# Global downloader instance
downloader = ModelDownloader() 