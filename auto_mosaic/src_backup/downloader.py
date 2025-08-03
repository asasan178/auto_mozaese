"""
自動モザエセ用モデルダウンローダー
Handles downloading and caching of ML model files
"""

import hashlib
import shutil
import time
import zipfile
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, List
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener, install_opener
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

from auto_mosaic.src.utils import get_models_dir, get_app_data_dir, 自動モザエセLogger

logger = 自動モザエセLogger(__name__)

class DownloadProgress:
    """Track download progress with callback support"""
    
    def __init__(self, total_size: int, callback: Optional[Callable[[int, int], None]] = None):
        self.total_size = total_size
        self.downloaded = 0
        self.callback = callback
        self.start_time = time.time()
        self.last_callback_time = 0
    
    def update(self, chunk_size: int):
        self.downloaded += chunk_size
        current_time = time.time()
        
        # Call callback every 0.1 seconds to avoid UI freezing
        if current_time - self.last_callback_time >= 0.1:
            if self.callback:
                self.callback(self.downloaded, self.total_size)
            self.last_callback_time = current_time
    
    def force_callback(self):
        """Force callback execution (for completion)"""
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
            "description": "YOLOv8m 中型モデル",
            "size": "50 MB",
            "filename": "yolov8m.pt",
            "type": "single"
        },
        "anime_nsfw_v4": {
            "description": "Anime NSFW Detection v4.0",
            "type": "zip",
            "filename": "animeNSFWDetection_v40.zip",
            "extract_dir": "anime_nsfw_v4",
            "size": "約100MB",
            "url": "https://civitai.com/api/download/models/1863248?type=Archive&format=Other",
            "fallback_urls": [
                "https://civitai.com/api/download/models/1863248?type=Archive&format=Other"
            ],
            "manual_url": "https://civitai.com/models/1313556?modelVersionId=1863248",
            "main_models": {
                "all": "ntd11_anime_nsfw_segm_v4_all.pt",
                "penis": "ntd11_anime_nsfw_segm_v4_penis.pt",
                "labia_minora": "ntd11_anime_nsfw_segm_v4_pussy.pt",
                "pussy": "ntd11_anime_nsfw_segm_v4_pussy.pt",
                "testicles": "ntd11_anime_nsfw_segm_v4_testicles.pt",
                "anus": "ntd11_anime_nsfw_segm_v4_anus.pt",
                "nipples": "ntd11_anime_nsfw_segm_v4_nipples.pt",
                "x-ray": "ntd11_anime_nsfw_segm_v4_x-ray.pt",
                "cross-section": "ntd11_anime_nsfw_segm_v4_cross-section.pt"
            }
        },
        "nudenet_models": {
            "description": "NudeNet detector models",
            "type": "runtime_download",
            "size": "約50MB",
            "install_package": "nudenet",
            "models": {
                "classifier": {
                    "url": "https://github.com/notAI-tech/NudeNet/releases/download/v0/classifier_model.onnx",
                    "filename": "classifier_model.onnx"
                },
                "detector": {
                    "url": "https://github.com/notAI-tech/NudeNet/releases/download/v0/detector_v2_default_checkpoint.onnx", 
                    "filename": "detector_v2_default_checkpoint.onnx"
                }
            }
        },
        "sam_vit_h": {
            "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
            "description": "SAM ViT-H セグメンテーションモデル",
            "size": "2.4 GB",
            "filename": "sam_vit_h.pth",
            "type": "single"
        },
        "sam_vit_b": {
            "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
            "description": "SAM ViT-B セグメンテーションモデル",
            "size": "358 MB", 
            "filename": "sam_vit_b.pth",
            "type": "single"
        }
    }
    
    def __init__(self):
        self.models_dir = get_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.civitai_api_key = None
        
        # Thread safety for logging
        self._log_lock = threading.Lock()
        
        # Download log file (compatible with old version)
        self.download_log = self.models_dir / "download.log"
        
        # Setup HTTP redirect handler for CivitAI
        redirect_handler = HTTPRedirectHandler()
        opener = build_opener(redirect_handler)
        install_opener(opener)
    
    def set_civitai_api_key(self, api_key: Optional[str]):
        """Set CivitAI API key for authenticated downloads"""
        self.civitai_api_key = api_key
        if api_key:
            logger.info("CivitAI API key configured")
        else:
            logger.info("CivitAI API key cleared")
    
    def _get_civitai_download_url(self, model_url: str) -> str:
        """Modify CivitAI URL to include API key if available"""
        if not self.civitai_api_key:
            return model_url
        
        # Parse URL to add token parameter
        parsed = urlparse(model_url)
        query_params = parse_qs(parsed.query)
        
        # Add token parameter
        query_params['token'] = [self.civitai_api_key]
        
        # Reconstruct URL
        from urllib.parse import urlencode, urlunparse
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return new_url
    
    def _log_download(self, message: str):
        """Log download activity to file (thread-safe)"""
        with self._log_lock:
            # Log to both locations for compatibility
            # 1. Models directory (old version compatibility)
            with open(self.download_log, "a", encoding="utf-8") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
            
            # 2. App data logs directory (new version)
            log_file = get_app_data_dir() / "logs" / "downloads.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
    
    def get_missing_models_info(self) -> Dict[str, Dict]:
        """Get information about missing models"""
        missing = {}
        
        for model_name, model_info in self.MODELS.items():
            if not self.is_model_available(model_name):
                missing[model_name] = {
                    "description": model_info["description"],
                    "size": model_info["size"],
                    "manual_url": model_info.get("manual_url", ""),
                    "type": model_info["type"]
                }
        
        return missing
    
    def smart_model_setup(self, progress_callback: Optional[Callable[[str, str, int, int], None]] = None) -> Dict[str, List]:
        """
        Intelligent model setup with automatic and manual download support
        
        Args:
            progress_callback: Optional callback (model_name, status, downloaded, total)
            
        Returns:
            Dict with results categorized by success/failure
        """
        results = {
            "success": [],
            "failed": [],
            "manual_required": [],
            "already_available": [],
            "downloaded": [],  # GUI compatibility
            "opened_in_browser": []  # GUI compatibility
        }
        
        missing_models = self.get_missing_models_info()
        
        if not missing_models:
            logger.info("✅ All required models are already available")
            for model_name in self.MODELS:
                results["already_available"].append(model_name)
            # GUI compatibility - no downloads needed
            results["downloaded"] = []
            results["opened_in_browser"] = []
            return results
        
        logger.info(f"🔍 Found {len(missing_models)} missing models")
        
        # Check for existing ZIP files first
        for model_name, model_info in missing_models.items():
            # Get full model info from MODELS dict (missing_models only has partial info)
            full_model_info = self.MODELS[model_name]
            zip_path = self.models_dir / full_model_info["filename"]
            if zip_path.exists():
                logger.info(f"📦 Found existing ZIP file: {zip_path.name}")
                if self._extract_existing_zip(full_model_info, zip_path):
                    results["success"].append(model_name)
                    results["downloaded"].append(model_name)  # GUI compatibility
                    if progress_callback:
                        progress_callback(model_name, "extracted", 100, 100)
                    continue
        
        # Update missing models after extraction
        remaining_missing = self.get_missing_models_info()
        
        for model_name, model_info in remaining_missing.items():
            # Get full model info from MODELS dict
            full_model_info = self.MODELS[model_name]
            logger.info(f"📥 Attempting to download: {full_model_info['description']}")
            
            if progress_callback:
                progress_callback(model_name, "downloading", 0, 100)
            
            # Create model-specific progress callback
            def model_progress(downloaded: int, total: int):
                if progress_callback:
                    progress_callback(model_name, "downloading", downloaded, total)
            
            try:
                success = self.download_model(model_name, model_progress)
                
                if success:
                    logger.info(f"✅ Successfully downloaded: {full_model_info['description']}")
                    results["success"].append(model_name)
                    results["downloaded"].append(model_name)  # GUI compatibility
                    if progress_callback:
                        progress_callback(model_name, "completed", 100, 100)
                else:
                    logger.warning(f"⚠️ Failed to download: {full_model_info['description']}")
                    results["failed"].append(model_name)
                    results["manual_required"].append(model_name)
                    if progress_callback:
                        progress_callback(model_name, "failed", 0, 100)
                        
            except Exception as e:
                logger.error(f"❌ Error downloading {full_model_info['description']}: {str(e)}")
                results["failed"].append(model_name)
                results["manual_required"].append(model_name)
                if progress_callback:
                    progress_callback(model_name, "error", 0, 100)
        
        # Handle manual downloads if needed
        if results["manual_required"]:
            logger.info(f"Opening manual download URLs for {len(results['manual_required'])} models")
            opened_urls = self.open_manual_download_urls(results["manual_required"])
            results["opened_in_browser"] = results["manual_required"].copy()
        
        # Log summary
        self._log_setup_summary(results)
        
        return results
    
    def _log_setup_summary(self, results: Dict[str, List]):
        """Log setup summary"""
        total_models = len(self.MODELS)
        successful = len(results["success"])
        already_available = len(results["already_available"])
        failed = len(results["failed"])
        
        logger.info(f"📊 Model Setup Summary:")
        logger.info(f"   Total models: {total_models}")
        logger.info(f"   Already available: {already_available}")
        logger.info(f"   Successfully downloaded: {successful}")
        logger.info(f"   Failed downloads: {failed}")
        
        if results["manual_required"]:
            logger.info(f"   Manual download required: {results['manual_required']}")
    
    def open_manual_download_urls(self, model_names: Optional[List[str]] = None) -> List[str]:
        """
        Open manual download URLs in browser
        
        Args:
            model_names: Specific models to open URLs for (None = all missing models)
            
        Returns:
            List of URLs that were opened
        """
        import webbrowser
        
        if model_names is None:
            model_names = list(self.get_missing_models_info().keys())
        
        opened_urls = []
        
        for model_name in model_names:
            if model_name in self.MODELS:
                model_info = self.MODELS[model_name]
                manual_url = model_info.get("manual_url")
                
                if manual_url:
                    logger.info(f"🌐 Opening manual download URL for {model_info['description']}")
                    webbrowser.open(manual_url)
                    opened_urls.append(manual_url)
                    time.sleep(1)  # Avoid overwhelming the browser
                else:
                    logger.warning(f"⚠️ No manual URL available for {model_name}")
        
        return opened_urls
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available locally"""
        # Handle legacy model name compatibility
        if model_name == "yolo_lite":
            model_name = "anime_nsfw_v4"
        
        if model_name not in self.MODELS:
            return False
        
        model_info = self.MODELS[model_name]
        
        if model_info["type"] == "zip":
            # Check if extracted directory exists with main models
            extract_dir = self.models_dir / model_info["extract_dir"]
            if not extract_dir.exists():
                return False
            
            # Check if at least the "all" model exists (like old version)
            main_model = extract_dir / model_info["main_models"]["all"]
            return main_model.exists() and main_model.stat().st_size > 0
        elif model_info["type"] == "runtime_download":
            # NudeNet models are handled by the package itself
            try:
                import nudenet
                return True  # If nudenet is installed, consider it available
            except ImportError:
                return False
        else:
            # Single file model with size check
            model_path = self.models_dir / model_info["filename"]
            return model_path.exists() and model_path.stat().st_size > 0
    
    def get_model_path(self, model_name: str, specific_model: str = "all") -> Optional[Path]:
        """Get path to a specific model file"""
        # Handle legacy model name compatibility
        if model_name == "yolo_lite":
            model_name = "anime_nsfw_v4"
        
        if not self.is_model_available(model_name):
            return None
        
        model_info = self.MODELS[model_name]
        
        if model_info["type"] == "zip":
            extract_dir = self.models_dir / model_info["extract_dir"]
            if specific_model in model_info["main_models"]:
                return extract_dir / model_info["main_models"][specific_model]
            else:
                return extract_dir / model_info["main_models"]["all"]
        elif model_info["type"] == "runtime_download":
            # NudeNet models are handled by the package itself
            logger.info(f"Runtime download model {model_name} path requested - handled by package")
            return None
        else:
            return self.models_dir / model_info["filename"]
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download model file if not already cached (compatible with old version)
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates (downloaded, total)
            
        Returns:
            True if successful, False otherwise
        """
        # Handle legacy model name compatibility
        if model_name == "yolo_lite":
            model_name = "anime_nsfw_v4"
            
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
                # Use fallback for CivitAI, otherwise direct download
                if 'civitai.com' in model_info["url"] and model_info.get("fallback_urls"):
                    return self._download_with_fallback(model_name, model_info, progress_callback)
                else:
                    return self._download_and_extract_zip(model_info, progress_callback)
            else:
                model_path = self.models_dir / model_info["filename"]
                return self._download_file(model_info["url"], model_path, progress_callback)
        except Exception as e:
            error_msg = f"Failed to download {model_name}: {str(e)}"
            logger.error(error_msg)
            self._log_download(f"ERROR: {error_msg}")
            return False

    def _download_with_fallback(self, model_name: str, model_info: Dict, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """CivitAI用のフォールバック機能 - 複数のURLを順番に試行"""
        logger.info(f"🔄 CivitAI フォールバック機能を開始: {model_info['description']}")
        
        # まず、CivitAI API v1で正しいモデルバージョンIDを動的に取得を試行
        if model_name == "anime_nsfw_v4":
            logger.info("🔍 Anime NSFW Detection v4.0の正しいバージョンIDを動的検索中...")
            
            # manual_urlからモデルIDを抽出
            manual_url = model_info.get("manual_url", "")
            if "models/" in manual_url:
                try:
                    model_id = manual_url.split("models/")[1].split("?")[0]
                    correct_version_id = self._find_correct_model_version_id(model_id)
                    
                    if correct_version_id:
                        # 正しいバージョンIDが見つかった場合、それを最優先で試行
                        dynamic_url = f"https://civitai.com/api/download/models/{correct_version_id}?type=Archive&format=Other"
                        logger.info(f"🎯 動的検索で発見したURL: {dynamic_url}")
                        
                        try:
                            return self._download_and_extract_zip({
                                **model_info,
                                "url": dynamic_url
                            }, progress_callback)
                        except Exception as e:
                            logger.error(f"❌ 動的検索URLでもダウンロード失敗: {str(e)}")
                            # 失敗した場合は、以下のフォールバック処理を続行
                    else:
                        logger.warning("⚠️ 動的検索でも正しいバージョンIDが見つかりませんでした")
                        
                except Exception as e:
                    logger.error(f"❌ 動的検索処理でエラー: {str(e)}")
        
        # 元のフォールバック処理（既存のfallback_urlsを試行）
        fallback_urls = model_info.get("fallback_urls", [model_info["url"]])
        
        for i, fallback_url in enumerate(fallback_urls, 1):
            logger.info(f"📥 フォールバックURL {i}/{len(fallback_urls)} を試行: {fallback_url}")
            
            try:
                result = self._download_and_extract_zip({
                    **model_info,
                    "url": fallback_url
                }, progress_callback)
                if result:
                    logger.info(f"✅ フォールバックURL {i} でダウンロード成功！")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ フォールバックURL {i} でエラー: {str(e)}")
                if "400" in str(e):
                    logger.error(f"   詳細: HTTP 400 Bad Request - モデルバージョンID無効")
                elif "404" in str(e):
                    logger.error(f"   詳細: HTTP 404 Not Found - モデルバージョンIDが存在しない")
                
                # 最後のURL以外は次のURLを試行
                if i < len(fallback_urls):
                    logger.info(f"🔄 次のフォールバックURLを試行...")
                    continue
        
        logger.error(f"❌ 全てのフォールバックURLでダウンロードに失敗しました")
        return False
    
    def _download_and_extract_zip(self, model_info: Dict, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download and extract zip file with improved UI responsiveness"""
        zip_path = self.models_dir / model_info["filename"]
        extract_dir = self.models_dir / model_info["extract_dir"]
        
        try:
            # Download zip file
            success = self._download_file(model_info["url"], zip_path, progress_callback)
            if not success:
                return False
            
            # Extract zip file with progress updates
            logger.info(f"Extracting {zip_path.name}...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                total_files = len(zip_ref.namelist())
                
                for i, member in enumerate(zip_ref.namelist()):
                    zip_ref.extract(member, extract_dir)
                    
                    # 抽出プログレス更新
                    if progress_callback and total_files > 0:
                        progress_callback(i + 1, total_files)
                    
                    # UIの応答性のための小さな遅延
                    if i % 5 == 0:  # 5ファイルごとに遅延
                        time.sleep(0.01)
            
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
        """Download file with progress tracking and UI responsiveness"""
        
        # CivitAI APIキーがある場合はURLを修正
        download_url = url
        if 'civitai.com' in url and self.civitai_api_key:
            download_url = self._get_civitai_download_url(url)
            logger.info(f"CivitAI APIキーを使用してダウンロードを開始")
            logger.info(f"Original URL: {url}")
            logger.info(f"Modified URL: {download_url}")
        
        # CivitAI向け2段階ダウンロード処理
        if 'civitai.com' in url:
            # Step 1: CivitAI API からリダイレクト先URLを取得
            request = Request(download_url)
            
            # Minimal headers like curl (avoid over-complicated headers)
            request.add_header('User-Agent', 'curl/7.68.0')  # Simple curl-like UA
            
            # Debug: Log request details
            headers_dict = dict(request.headers)
            logger.info(f"🔗 Minimal headers: {headers_dict}")
            
            try:
                # Step 1: Get redirect URL from CivitAI API
                logger.info(f"🔄 Getting redirect URL from CivitAI API: {download_url}")
                with urlopen(request, timeout=30) as response:
                    # レスポンスのContent-Typeを確認
                    content_type = response.headers.get('content-type', 'unknown')
                    content_length = response.headers.get('content-length', '0')
                    logger.info(f"📊 CivitAI API response content-type: {content_type}")
                    logger.info(f"📊 CivitAI API response content-length: {content_length}")
                    
                    # Content-Typeをチェックして処理を分岐
                    if 'text' in content_type.lower() or 'json' in content_type.lower():
                        # テキストレスポンス（リダイレクトURL）の場合
                        redirect_url = response.read().decode('utf-8').strip()
                        logger.info(f"🎯 CivitAI API returned redirect URL: {redirect_url}")
                        
                        # URLが有効かチェック
                        if not redirect_url.startswith('https://'):
                            raise Exception(f"Invalid redirect URL received: {redirect_url}")
                        
                        # Step 2: Download from the actual file URL
                        logger.info(f"📥 Downloading from actual file URL: {redirect_url}")
                        file_request = Request(redirect_url)
                        file_request.add_header('User-Agent', 'curl/7.68.0')
                        
                        with urlopen(file_request, timeout=30) as file_response:
                            total_size = int(file_response.headers.get('content-length', 0))
                            content_type = file_response.headers.get('content-type', 'unknown')
                            content_disposition = file_response.headers.get('content-disposition', 'unknown')
                            
                            logger.info(f"📊 File response content-type: {content_type}")
                            logger.info(f"📊 File response content-disposition: {content_disposition}")
                            logger.info(f"📊 File response content-length: {total_size}")
                            
                            if total_size == 0:
                                logger.warning("⚠️ Unable to determine file size")
                            else:
                                logger.info(f"📦 File size: {total_size / (1024*1024):.1f} MB")
                            
                            progress = DownloadProgress(total_size, progress_callback)
                            
                            # Download to temporary file first
                            temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
                            
                            with open(temp_path, "wb") as f:
                                chunk_size = 4096
                                update_interval = 32
                                chunk_count = 0
                                
                                while True:
                                    chunk = file_response.read(chunk_size)
                                    if not chunk:
                                        break
                                    
                                    f.write(chunk)
                                    progress.update(len(chunk))
                                    
                                    chunk_count += 1
                                    if chunk_count % update_interval == 0:
                                        f.flush()
                                        time.sleep(0.001)
                    else:
                        # バイナリレスポンス（直接ファイル）の場合
                        logger.info("🎯 CivitAI API returned file directly (no redirect)")
                        total_size = int(content_length)
                        
                        if total_size == 0:
                            logger.warning("⚠️ Unable to determine file size")
                        else:
                            logger.info(f"📦 File size: {total_size / (1024*1024):.1f} MB")
                        
                        progress = DownloadProgress(total_size, progress_callback)
                        
                        # Download to temporary file first
                        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
                        
                        with open(temp_path, "wb") as f:
                            chunk_size = 4096
                            update_interval = 32
                            chunk_count = 0
                            
                            while True:
                                chunk = response.read(chunk_size)
                                if not chunk:
                                    break
                                
                                f.write(chunk)
                                progress.update(len(chunk))
                                
                                chunk_count += 1
                                if chunk_count % update_interval == 0:
                                    f.flush()
                                    time.sleep(0.001)
                    
                    # 共通の後処理
                    progress.force_callback()
                    shutil.move(str(temp_path), str(target_path))
                    
                    logger.info(f"Successfully downloaded {target_path.name} ({progress.downloaded / (1024*1024):.1f} MB)")
                    self._log_download(f"SUCCESS: Downloaded {target_path.name}")
                    
                    return True
                    
            except (URLError, HTTPError) as e:
                error_msg = str(e)
                logger.error(f"Network error details: {error_msg}")
                
                if 'HTTP Error 400' in error_msg:
                    raise Exception(f"CivitAI API Bad Request (400): URLまたはAPIキーが正しくない可能性があります。\n詳細: {error_msg}")
                elif 'HTTP Error 401' in error_msg:
                    if self.civitai_api_key:
                        raise Exception(f"CivitAI APIキーが無効です (401): {error_msg}")
                    else:
                        raise Exception(f"CivitAI APIキーが必要です (401): {error_msg}")
                elif 'HTTP Error 403' in error_msg:
                    raise Exception(f"CivitAI API Forbidden (403): アクセス権限がありません。\n詳細: {error_msg}")
                else:
                    raise Exception(f"CivitAI API認証エラー: {error_msg}")
        else:
            # Non-CivitAI downloads (regular downloads)
            request = Request(download_url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            request.add_header('Accept', '*/*')
            request.add_header('Accept-Language', 'en-US,en;q=0.9,ja;q=0.8')
            request.add_header('Accept-Encoding', 'gzip, deflate, br')
            request.add_header('Connection', 'keep-alive')
            request.add_header('Upgrade-Insecure-Requests', '1')
            
            try:
                with urlopen(request) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    
                    if total_size == 0:
                        logger.warning("Unable to determine file size")
                    
                    progress = DownloadProgress(total_size, progress_callback)
                    
                    # Download to temporary file first
                    temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
                    
                    with open(temp_path, "wb") as f:
                        chunk_size = 4096
                        update_interval = 32
                        chunk_count = 0
                        
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            
                            f.write(chunk)
                            progress.update(len(chunk))
                            
                            chunk_count += 1
                            if chunk_count % update_interval == 0:
                                f.flush()
                                time.sleep(0.001)
                        
                        progress.force_callback()
                    shutil.move(str(temp_path), str(target_path))
                    
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
            extract_dir.mkdir(parents=True, exist_ok=True)
            
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

    def _find_correct_model_version_id(self, model_id: str) -> Optional[str]:
        """CivitAI API v1を使って正しいモデルバージョンIDを取得"""
        try:
            import json
            api_url = f"https://civitai.com/api/v1/models/{model_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # APIキーがある場合は認証ヘッダーを追加
            if self.civitai_api_key:
                headers['Authorization'] = f'Bearer {self.civitai_api_key}'
                api_url += f"?token={self.civitai_api_key}"
            
            logger.info(f"🔍 CivitAI API v1でモデル情報を取得中: {model_id}")
            
            request = Request(api_url)
            for key, value in headers.items():
                request.add_header(key, value)
            
            with urlopen(request, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    if 'modelVersions' in data and data['modelVersions']:
                        # 最新のバージョンを取得（通常は最初の要素）
                        latest_version = data['modelVersions'][0]
                        version_id = str(latest_version['id'])
                        version_name = latest_version.get('name', 'Unknown')
                        
                        logger.info(f"✅ 最新バージョンを発見: {version_name} (ID: {version_id})")
                        return version_id
                    else:
                        logger.warning(f"⚠️ モデル {model_id} にバージョン情報が見つかりません")
                        return None
                else:
                    logger.error(f"❌ CivitAI API v1 エラー: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ CivitAI API v1 調査でエラー: {str(e)}")
            return None

# Global downloader instance
downloader = ModelDownloader() 