
import os
import sys
import ctypes
import platform

# 配布版では開発者モードを強制的に無効化
os.environ['AUTO_MOSAIC_DEV_MODE'] = 'false'
os.environ['DEVELOPER_MODE'] = 'false'

# Windows DLL処理の強化
def fix_windows_dll_loading():
    """Windows環境でのDLL読み込み問題を修正"""
    if platform.system() == 'Windows':
        # Windows DLL検索パスを追加
        if hasattr(sys, '_MEIPASS'):
            dll_dir = sys._MEIPASS
            try:
                # SetDllDirectoryW を使用してDLL検索パスを設定
                ctypes.windll.kernel32.SetDllDirectoryW(dll_dir)
                # AddDllDirectory も使用（Windows 7以降）
                try:
                    ctypes.windll.kernel32.AddDllDirectory(dll_dir)
                except AttributeError:
                    # Windows 7未満では利用できない
                    pass
            except Exception:
                # DLL操作に失敗した場合はPATHで代用
                pass

# Windows DLL読み込みを修正
fix_windows_dll_loading()

# ONNXRuntimeのDLLパスを設定
if hasattr(sys, '_MEIPASS'):
    # PyInstallerの一時ディレクトリにDLLパスを追加
    dll_path = sys._MEIPASS
    current_path = os.environ.get('PATH', '')
    if dll_path not in current_path:
        os.environ['PATH'] = dll_path + os.pathsep + current_path
    
    # ONNXRuntimeの特定のDLLディレクトリも追加
    onnx_dll_path = os.path.join(dll_path, 'onnxruntime', 'capi')
    if os.path.exists(onnx_dll_path) and onnx_dll_path not in current_path:
        os.environ['PATH'] = onnx_dll_path + os.pathsep + os.environ['PATH']
        # Windows DLL検索パスにも追加
        try:
            ctypes.windll.kernel32.AddDllDirectory(onnx_dll_path)
        except (AttributeError, OSError):
            pass
    
    # LD_LIBRARY_PATH も設定（Linux用だが念のため）
    if 'LD_LIBRARY_PATH' in os.environ:
        os.environ['LD_LIBRARY_PATH'] = dll_path + os.pathsep + os.environ['LD_LIBRARY_PATH']
    else:
        os.environ['LD_LIBRARY_PATH'] = dll_path

# ONNXRuntime環境変数を設定
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['ORT_LOGGING_LEVEL'] = '3'
os.environ['ORT_PROVIDERS'] = 'CPUExecutionProvider'

# Microsoft Visual C++ Redistributableの問題を回避
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# ONNXRuntimeの事前ロード（DLL依存関係を解決）
def preload_onnxruntime():
    """ONNXRuntimeのDLLを事前ロードしてDLL依存関係を解決"""
    if hasattr(sys, '_MEIPASS') and platform.system() == 'Windows':
        try:
            # Microsoft Visual C++ Runtime DLLを事前にロード（ONNXRuntime依存関係）
            runtime_dlls = [
                'msvcp140.dll',
                'vcruntime140.dll',
                'vcruntime140_1.dll'
            ]
            
            for runtime_dll in runtime_dlls:
                runtime_path = os.path.join(sys._MEIPASS, runtime_dll)
                if os.path.exists(runtime_path):
                    try:
                        ctypes.windll.kernel32.LoadLibraryW(runtime_path)
                    except OSError:
                        pass
                        
            # ONNXRuntime DLLを事前にロード
            dll_names = [
                'onnxruntime_providers_shared.dll',
                'onnxruntime.dll',
                'onnxruntime_providers_cuda.dll'
            ]
            
            for dll_name in dll_names:
                dll_path = os.path.join(sys._MEIPASS, dll_name)
                if os.path.exists(dll_path):
                    try:
                        ctypes.windll.kernel32.LoadLibraryW(dll_path)
                    except OSError:
                        # DLLロードに失敗しても続行
                        pass
                        
                # capiディレクトリからもロード
                capi_dll_path = os.path.join(sys._MEIPASS, 'onnxruntime', 'capi', dll_name)
                if os.path.exists(capi_dll_path):
                    try:
                        ctypes.windll.kernel32.LoadLibraryW(capi_dll_path)
                    except OSError:
                        pass
        except Exception:
            # 事前ロードに失敗しても続行
            pass

# ONNXRuntimeの事前ロードを実行
preload_onnxruntime()
