# -*- mode: python ; coding: utf-8 -*-
"""
自動モザエセ v1.2 - Distribution Build Configuration
配布版ビルド設定（統合認証・カスタムモデル・遅延ローダー対応）
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files, collect_submodules, collect_all

# プロジェクトのルートディレクトリ
project_root = Path.cwd()
auto_mosaic_src = project_root / "auto_mosaic" / "src"

# ONNXRuntimeの依存DLLを探す関数
def find_onnxruntime_dlls():
    """Find all ONNX Runtime DLL dependencies"""
    dll_files = []
    
    # ONNXRuntimeのインストール場所を探す
    import site
    import onnxruntime
    
    # ONNXRuntimeのパッケージディレクトリ
    onnx_path = os.path.dirname(onnxruntime.__file__)
    print(f"ONNXRuntime path: {onnx_path}")
    
    # DLLファイルを探す
    for root, dirs, files in os.walk(onnx_path):
        for file in files:
            if file.endswith('.dll'):
                dll_path = os.path.join(root, file)
                dll_files.append((dll_path, '.'))
                print(f"Found ONNX DLL: {dll_path}")
    
    return dll_files

# NudeNetモデルファイルを探す関数
def find_nudenet_models():
    """Find NudeNet model files for inclusion in the executable"""
    model_files = []
    
    # 一般的なNudeNetモデルの保存場所を探す
    import site
    import os
    
    # ユーザーのホームディレクトリの.nudenetフォルダ
    home_dir = os.path.expanduser("~")
    nudenet_dir = os.path.join(home_dir, ".nudenet")
    
    if os.path.exists(nudenet_dir):
        for root, dirs, files in os.walk(nudenet_dir):
            for file in files:
                if file.endswith('.onnx'):  # すべてのONNXファイルを含める
                    model_path = os.path.join(root, file)
                    model_files.append((model_path, f"nudenet_models/{os.path.basename(file)}"))
                    print(f"Found NudeNet model: {model_path}")
    
    # site-packagesのnudenetフォルダも探す
    for site_dir in site.getsitepackages():
        nudenet_pkg_dir = os.path.join(site_dir, "nudenet")
        if os.path.exists(nudenet_pkg_dir):
            for root, dirs, files in os.walk(nudenet_pkg_dir):
                for file in files:
                    if file.endswith('.onnx'):  # すべてのONNXファイルを含める
                        model_path = os.path.join(root, file)
                        model_files.append((model_path, f"nudenet_models/{os.path.basename(file)}"))
                        print(f"Found NudeNet model in package: {model_path}")
    
    return model_files



# ランタイムフック用のスクリプトを作成（配布版専用の開発者モード無効化を追加）
runtime_hook_content = '''
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
'''

# ランタイムフックファイルを作成
runtime_hook_path = 'runtime_hook_onnx_distribution.py'
with open(runtime_hook_path, 'w', encoding='utf-8') as f:
    f.write(runtime_hook_content)

# ONNXRuntimeのDLLファイルを取得
try:
    onnxruntime_dlls = find_onnxruntime_dlls()
except Exception as e:
    print(f"Warning: Could not find ONNX Runtime DLLs: {e}")
    onnxruntime_dlls = []

# NudeNetモデルファイルを取得
nudenet_models = find_nudenet_models()

# encodingsモジュールを強制的に含める
encodings_datas, encodings_binaries, encodings_hiddenimports = collect_all('encodings')

# 分析設定
a = Analysis(
    ['../auto_mosaic/__main__.py'],
    pathex=[str(project_root)],
    binaries=[
        # ONNXランタイムのネイティブライブラリを含める
        # Microsoft Visual C++ Runtime DLLs（ONNXRuntime依存関係）
        ('C:\\Windows\\System32\\msvcp140.dll', '.'),
        ('C:\\Windows\\System32\\vcruntime140.dll', '.'),
        ('C:\\Windows\\System32\\vcruntime140_1.dll', '.'),
    ] + collect_dynamic_libs('onnxruntime') + onnxruntime_dlls + encodings_binaries,
    datas=[
        # アイコンファイル（存在する場合）
        ('../icon.ico', '.'),
        ('../icon.png', '.'),
        
        # NudeNetモデルファイル（事前ダウンロードされたファイルを含める）
        ('../nudenet_models/detector_v2_default_checkpoint.onnx', '.'),
        ('../nudenet_models/classifier_model.onnx', '.'),
        ('../nudenet_models/320n.onnx', '.'),
        
        # auto_mosaicのソースファイルを明示的に含める
        ('../auto_mosaic/src/detector.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/nudenet_detector.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/segmenter.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/mosaic.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/gui.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/utils.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/downloader.py', 'auto_mosaic/src/'),
        
        # ★ 新機能ファイル（v1.2対応）
        ('../auto_mosaic/src/auth.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/auth_config.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/auth_manager.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/discord_auth_adapter.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/encrypted_config.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/env_config.py', 'auto_mosaic/src/'),
        ('../auto_mosaic/src/lazy_loader.py', 'auto_mosaic/src/'),
        
        # パッケージ初期化ファイル
        ('../auto_mosaic/__init__.py', 'auto_mosaic/'),
        ('../auto_mosaic/src/__init__.py', 'auto_mosaic/src/'),
        
        # ドキュメントファイル
        ('../docs/user_guide.html', 'docs/'),
        ('../docs/images/discord_code_success.png', 'docs/images/'),
        ('../docs/images/discord_auth_page.png', 'docs/images/'),
        ('../docs/images/discord_auth_success.png', 'docs/images/'),
        ('../docs/images/discord_auth_start.png', 'docs/images/'),
        ('../docs/images/setup_complete.png', 'docs/images/'),
        ('../docs/images/welcome_screen.png', 'docs/images/'),
        ('../docs/images/initial_setup_dialog.png', 'docs/images/'),
        ('../docs/images/civitai_api_setup.png', 'docs/images/'),
        ('../docs/images/main_settings_screen.png', 'docs/images/'),
        ('../docs/images/input_output_settings.png', 'docs/images/'),
    ] + collect_data_files('nudenet') + nudenet_models + encodings_datas,
    hiddenimports=[
        # tkinter関連
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        
        # PyTorch関連（軽量化のため最小限）
        'torch',
        'torchvision',
        'torch.nn',
        'torch.nn.functional',
        
        # OpenCV関連
        'cv2',
        
        # その他必要なモジュール
        'numpy',
        'PIL',
        'PIL.Image',
        'requests',
        'urllib3',
        'tqdm',
        'pathlib',
        'threading',
        'queue',
        'json',
        'logging',
        'time',
        'os',
        'sys',
        'webbrowser',
        
        # ONNXRuntime関連（NudeNet用）
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        
        # NudeNet関連（実際に存在するモジュールのみ）
        'nudenet',
        'nudenet.nudenet',
        
        # ★ 新機能依存関係（v1.2対応）
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'dotenv',
        'base64',
        'hashlib',
        
        # 基本的なPythonモジュール（PyInstallerで問題が起きやすいもの）
        'encodings',
        'encodings.utf_8',
        'encodings.cp1252',
        'encodings.latin1',
        'codecs',
        'locale',
        'collections',
        'collections.abc',
        'functools',
        'itertools',
        'operator',
        'copy',
        'pickle',
        'io',
        'struct',
        
        # NudeNet関連（実際に存在するモジュールのみ）
        'nudenet',
        'nudenet.nudenet',
        
        # 自動モザエセの全モジュール（新機能含む）
        'auto_mosaic',
        'auto_mosaic.src',
        'auto_mosaic.src.auth',
        'auto_mosaic.src.auth_config',
        'auto_mosaic.src.auth_manager',
        'auto_mosaic.src.detector',
        'auto_mosaic.src.discord_auth_adapter',
        'auto_mosaic.src.downloader',
        'auto_mosaic.src.encrypted_config',
        'auto_mosaic.src.env_config',
        'auto_mosaic.src.gui',
        'auto_mosaic.src.lazy_loader',
        'auto_mosaic.src.mosaic',
        'auto_mosaic.src.nudenet_detector',
        'auto_mosaic.src.segmenter',
        'auto_mosaic.src.utils',
        
        # ONNXRuntime関連（完全な依存関係）
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.backend',
        'onnxruntime.backend.backend',
        'onnxruntime.tools',
        'onnxruntime.tools.symbolic_shape_infer',
        
        # SAM関連
        'segment_anything',
        
        # Ultralytics関連
        'ultralytics',
        'ultralytics.models',
        'ultralytics.models.yolo',
        
        # Windows関連
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        'pythoncom',
    ] + collect_submodules('onnxruntime') + collect_submodules('nudenet') + encodings_hiddenimports,  # ONNXRuntimeとNudeNetとencodingsの全サブモジュールを含める
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[runtime_hook_path],  # ランタイムフックを追加
    excludes=[
        # 最小限の除外のみ（基本的なPythonモジュールは絶対に除外しない）
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# DLL分離のための設定
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 実行ファイル設定（配布版）
exe = EXE(
    pyz,
    a.scripts,
    [],  # binariesを空にしてDLL分離
    exclude_binaries=True,  # DLL分離を有効化
    name='自動モザエセ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX圧縮を無効化（安定性のため）
    console=False,  # コンソールウィンドウを非表示（配布版）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon='../icon.ico',
    codesign_identity=None,
    entitlements_file=None,
    # アイコン設定（存在する場合）
    # icon='icon.ico',
)

# DLL収集設定
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # DLLのUPX圧縮も無効化（安定性のため）
    upx_exclude=[
        # 圧縮すると問題が起きる可能性があるDLLを除外
        'vcruntime*.dll',
        'msvcp*.dll',
        'api-ms-*.dll',
        'ucrtbase.dll',
        'torch*.dll',
        'cuda*.dll',
        'cudnn*.dll',
        'cublas*.dll',
        'cufft*.dll',
        'curand*.dll',
        'cusolver*.dll',
        'cusparse*.dll',
        'nvrtc*.dll',
        'nvToolsExt*.dll',
        'nvJitLink*.dll',
        # ONNXRuntime DLLも圧縮しない
        'onnxruntime*.dll',
        'onnxruntime_providers*.dll',
    ],
    name='自動モザエセ_配布版'
) 
