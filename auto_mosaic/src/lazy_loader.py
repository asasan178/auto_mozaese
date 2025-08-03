"""
Lazy Loader for Heavy Dependencies
大きなライブラリの遅延ロード（動的インポート）システム

exe化時のファイルサイズを削減するため、
重いライブラリを必要時にのみロードします。
"""

import sys
import os
import importlib
from pathlib import Path
from typing import Any, Optional, Dict
import threading


class LazyLoader:
    """遅延ローダークラス"""
    
    def __init__(self):
        self._loaded_modules: Dict[str, Any] = {}
        self._loading_lock = threading.Lock()
        self._external_dll_path = self._get_external_dll_path()
        
    def _get_external_dll_path(self) -> Optional[Path]:
        """外部DLLパスを取得"""
        if getattr(sys, 'frozen', False):
            # exe化環境
            exe_dir = Path(sys.executable).parent
            
            # 候補パス
            dll_candidates = [
                exe_dir / "cuda_libs",     # CUDA DLLs専用
                exe_dir / "external_libs", # 一般ライブラリ
                exe_dir / "dlls",
                exe_dir / "libs", 
                exe_dir,  # 実行ファイルと同じディレクトリ
            ]
            
            for dll_path in dll_candidates:
                if dll_path.exists():
                    return dll_path
                    
        return None
    
    def _get_cuda_dll_path(self) -> Optional[Path]:
        """CUDA専用DLLパスを取得"""
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            cuda_dir = exe_dir / "cuda_libs"
            if cuda_dir.exists():
                return cuda_dir
        return None
    
    def _setup_dll_path(self):
        """DLLパスをシステムパスに追加"""
        # CUDA DLLパスを優先で追加
        cuda_path = self._get_cuda_dll_path()
        if cuda_path:
            cuda_path_str = str(cuda_path)
            if cuda_path_str not in sys.path:
                sys.path.insert(0, cuda_path_str)
            
            # CUDA環境変数設定
            os.environ['CUDA_PATH'] = cuda_path_str
            
            # Windows DLL検索パスに追加
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(cuda_path_str)
                except Exception:
                    pass
                    
            # PATH環境変数に優先で追加
            current_path = os.environ.get('PATH', '')
            if cuda_path_str not in current_path:
                os.environ['PATH'] = cuda_path_str + os.pathsep + current_path
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"[LAZY LOADER] CUDA DLLパスを追加: {cuda_path_str}")
                except Exception:
                    pass
        
        # 一般外部DLLパス
        if self._external_dll_path:
            dll_path_str = str(self._external_dll_path)
            if dll_path_str not in sys.path:
                sys.path.insert(0, dll_path_str)
                
            # Windows DLL検索パスに追加
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(dll_path_str)
                except Exception:
                    pass
                    
            # PATH環境変数に追加
            current_path = os.environ.get('PATH', '')
            if dll_path_str not in current_path:
                os.environ['PATH'] = dll_path_str + os.pathsep + current_path
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"[LAZY LOADER] 外部DLLパスを追加: {dll_path_str}")
                except Exception:
                    pass
    
    def load_module(self, module_name: str, fallback_error: bool = True) -> Optional[Any]:
        """モジュールを遅延ロード"""
        with self._loading_lock:
            # すでにロード済みの場合
            if module_name in self._loaded_modules:
                return self._loaded_modules[module_name]
            
            try:
                # DLLパスのセットアップ
                self._setup_dll_path()
                
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"[LAZY LOADER] Loading {module_name}...")
                except Exception:
                    pass
                
                # モジュールをインポート
                module = importlib.import_module(module_name)
                self._loaded_modules[module_name] = module
                
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"[LAZY LOADER] ✅ {module_name} loaded successfully")
                except Exception:
                    pass
                return module
                
            except ImportError as e:
                error_msg = f"[LAZY LOADER] ❌ Failed to load {module_name}: {e}"
                # エラーメッセージは開発者モードでのみ表示
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(error_msg)
                except Exception:
                    pass
                
                if fallback_error:
                    raise ImportError(f"Required module '{module_name}' not available. "
                                    f"Please ensure it's installed or placed in the external libs directory.")
                return None
                
            except Exception as e:
                error_msg = f"[LAZY LOADER] ❌ Unexpected error loading {module_name}: {e}"
                # エラーメッセージは開発者モードでのみ表示
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(error_msg)
                except Exception:
                    pass
                return None
    
    def is_module_available(self, module_name: str) -> bool:
        """モジュールが利用可能かチェック"""
        try:
            module = self.load_module(module_name, fallback_error=False)
            return module is not None
        except Exception:
            return False
    
    def get_module_info(self) -> Dict[str, Any]:
        """ロード状況の情報を取得"""
        return {
            "loaded_modules": list(self._loaded_modules.keys()),
            "external_dll_path": str(self._external_dll_path) if self._external_dll_path else None,
            "dll_path_exists": self._external_dll_path.exists() if self._external_dll_path else False,
        }


# グローバルローダーインスタンス
_global_loader = LazyLoader()

def load_cv2():
    """OpenCV (cv2) を遅延ロード"""
    return _global_loader.load_module('cv2')

def load_numpy():
    """NumPy を遅延ロード"""
    return _global_loader.load_module('numpy')

def load_torch():
    """PyTorch を遅延ロード"""
    return _global_loader.load_module('torch')

def load_torchvision():
    """torchvision を遅延ロード"""
    return _global_loader.load_module('torchvision')

def load_ultralytics():
    """ultralytics (YOLO) を遅延ロード"""
    return _global_loader.load_module('ultralytics')

def load_segment_anything():
    """Segment Anything Model を遅延ロード"""
    return _global_loader.load_module('segment_anything')

def check_dependencies() -> Dict[str, bool]:
    """全ての依存関係をチェック"""
    dependencies = {
        'cv2': _global_loader.is_module_available('cv2'),
        'numpy': _global_loader.is_module_available('numpy'),
        'torch': _global_loader.is_module_available('torch'),
        'torchvision': _global_loader.is_module_available('torchvision'),
        'ultralytics': _global_loader.is_module_available('ultralytics'),
        'segment_anything': _global_loader.is_module_available('segment_anything'),
    }
    return dependencies

def get_loader_info() -> Dict[str, Any]:
    """ローダー情報を取得"""
    return _global_loader.get_module_info()

def install_missing_dependencies():
    """不足している依存関係のインストールを試行"""
    import subprocess
    
    dependencies = check_dependencies()
    missing = [name for name, available in dependencies.items() if not available]
    
    if not missing:
        try:
            from auto_mosaic.src.utils import is_developer_mode
            if is_developer_mode():
                print("✅ All dependencies are available")
        except Exception:
            pass
        return True
    
    try:
        from auto_mosaic.src.utils import is_developer_mode
        if is_developer_mode():
            print(f"⚠️ Missing dependencies: {missing}")
    except Exception:
        pass
    
    # pip install を試行
    pip_mapping = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'torch': 'torch',
        'torchvision': 'torchvision', 
        'ultralytics': 'ultralytics',
        'segment_anything': 'git+https://github.com/facebookresearch/segment-anything.git',
    }
    
    for dep in missing:
        if dep in pip_mapping:
            try:
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"Installing {dep}...")
                except Exception:
                    pass
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', 
                    pip_mapping[dep]
                ])
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"✅ {dep} installed successfully")
                except Exception:
                    pass
            except subprocess.CalledProcessError as e:
                try:
                    from auto_mosaic.src.utils import is_developer_mode
                    if is_developer_mode():
                        print(f"❌ Failed to install {dep}: {e}")
                except Exception:
                    pass
                return False
    
    return True


if __name__ == "__main__":
    # テスト実行（開発者モードでのみ表示）
    try:
        from auto_mosaic.src.utils import is_developer_mode
        show_output = is_developer_mode()
    except Exception:
        show_output = True  # 直接実行時は表示
    
    if show_output:
        print("=== Lazy Loader Test ===")
        
        # 情報表示
        info = get_loader_info()
        print(f"External DLL path: {info['external_dll_path']}")
        print(f"DLL path exists: {info['dll_path_exists']}")
        
        # 依存関係チェック
        deps = check_dependencies()
        print("\nDependency check:")
        for name, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {name}")
        
        # 不足している場合はインストールを試行
        if not all(deps.values()):
            print("\nAttempting to install missing dependencies...")
            install_missing_dependencies() 