# -*- mode: python ; coding: utf-8 -*-
"""
自動モザエセ - Lightweight Build with DLL Separation
軽量版ビルド設定（DLL分離構成）
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
                if file.endswith('.onnx') and '320n' not in file:  # 問題のあるファイルを除外
                    model_path = os.path.join(root, file)
                    model_files.append((model_path, f"nudenet_models/{os.path.basename(file)}"))
                    print(f"Found NudeNet model: {model_path}")
    
    # site-packagesのnudenetフォルダも探す（320n.onnxを除外）
    for site_dir in site.getsitepackages():
        nudenet_pkg_dir = os.path.join(site_dir, "nudenet")
        if os.path.exists(nudenet_pkg_dir):
            for root, dirs, files in os.walk(nudenet_pkg_dir):
                for file in files:
                    if file.endswith('.onnx') and '320n' not in file:  # 問題のあるファイルを除外
                        model_path = os.path.join(root, file)
                        model_files.append((model_path, f"nudenet_models/{os.path.basename(file)}"))
                        print(f"Found NudeNet model in package: {model_path}")
    
    return model_files

# NudeNetの320n.onnxファイルを手動で作成する関数
def create_nudenet_320n_model():
    """Create 320n.onnx file from detector_v2_default_checkpoint.onnx"""
    import os
    import shutil
    
    source_model = "nudenet_models/detector_v2_default_checkpoint.onnx"
    target_320n = "nudenet_models/320n.onnx"
    
    if os.path.exists(source_model) and not os.path.exists(target_320n):
        try:
            shutil.copy2(source_model, target_320n)
            print(f"Created 320n.onnx from {source_model}")
            return [(target_320n, "320n.onnx")]
        except Exception as e:
            print(f"Failed to create 320n.onnx: {e}")
            return []
    elif os.path.exists(target_320n):
        print(f"320n.onnx already exists: {target_320n}")
        return [(target_320n, "320n.onnx")]
    else:
        print(f"Source model not found: {source_model}")
        return []

# ランタイムフック用のスクリプトを作成
runtime_hook_content = '''
import os
import sys

# ONNXRuntimeのDLLパスを設定
if hasattr(sys, '_MEIPASS'):
    # PyInstallerの一時ディレクトリにDLLパスを追加
    dll_path = sys._MEIPASS
    if dll_path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
    
    # LD_LIBRARY_PATH も設定（Linux用だが念のため）
    if 'LD_LIBRARY_PATH' in os.environ:
        os.environ['LD_LIBRARY_PATH'] = dll_path + os.pathsep + os.environ['LD_LIBRARY_PATH']
    else:
        os.environ['LD_LIBRARY_PATH'] = dll_path

# ONNXRuntime環境変数を設定
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['ORT_LOGGING_LEVEL'] = '3'
'''

# ランタイムフックファイルを作成
runtime_hook_path = 'runtime_hook_onnx.py'
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

# 320n.onnxファイルを作成
nudenet_320n = create_nudenet_320n_model()

# encodingsモジュールを強制的に含める
encodings_datas, encodings_binaries, encodings_hiddenimports = collect_all('encodings')

# 分析設定
a = Analysis(
    ['../auto_mosaic/__main__.py'],
    pathex=[str(project_root)],
    binaries=[
        # ONNXランタイムのネイティブライブラリを含める
    ] + collect_dynamic_libs('onnxruntime') + onnxruntime_dlls + encodings_binaries,
    datas=[
        # アイコンファイル（存在する場合）
        # ('icon.ico', '.'),
        
        # NudeNetモデルファイル（事前ダウンロードされたファイルを含める）
        ('nudenet_models/detector_v2_default_checkpoint.onnx', '.'),
        ('nudenet_models/classifier_model.onnx', '.'),
        
        # NudeNetパッケージ全体を強制的に含める
    ] + collect_data_files('nudenet') + nudenet_models + nudenet_320n + encodings_datas,
    hiddenimports=[
        # 必要な隠れたインポート
        'auto_mosaic.src.gui',
        'auto_mosaic.src.detector',
        'auto_mosaic.src.segmenter',
        'auto_mosaic.src.mosaic',
        'auto_mosaic.src.utils',
        'auto_mosaic.src.auth',
        'auto_mosaic.src.downloader',
        'auto_mosaic.src.lazy_loader',
        
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

# 実行ファイル設定（軽量化）
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
    name='自動モザエセ_軽量版'
) 
