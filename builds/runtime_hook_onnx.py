
import os
import sys
import ctypes
import platform

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
