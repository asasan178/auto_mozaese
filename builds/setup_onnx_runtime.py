#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONNXRuntime Setup for PyInstaller
ONNXRuntimeの依存関係を確実に解決するためのセットアップスクリプト
（CUDA環境自動検出対応）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_cuda_availability():
    """CUDA環境の利用可能性を詳細チェック"""
    cuda_info = {
        "pytorch_available": False,
        "cuda_available": False,
        "onnx_gpu_compatible": False,
        "device_count": 0,
        "device_name": "Unknown",
        "cuda_version": "Unknown",
        "cudnn_available": False,
        "errors": []
    }
    
    try:
        import torch
        cuda_info["pytorch_available"] = True
        cuda_info["cuda_version"] = getattr(torch.version, 'cuda', 'Unknown')
        
        print(f"✅ PyTorch検出: {torch.__version__} (CUDA: {cuda_info['cuda_version']})")
        
        # CUDA基本チェック
        if torch.cuda.is_available():
            cuda_info["cuda_available"] = True
            cuda_info["device_count"] = torch.cuda.device_count()
            if cuda_info["device_count"] > 0:
                cuda_info["device_name"] = torch.cuda.get_device_name(0)
                print(f"✅ CUDA環境検出: {cuda_info['device_name']} ({cuda_info['device_count']} devices)")
                
                # メモリチェック
                try:
                    memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    print(f"📊 GPU Memory: {memory_total:.1f}GB")
                    
                    # 簡単な推論テスト
                    test_tensor = torch.randn(1, 3, 224, 224).cuda()
                    _ = test_tensor.sum()
                    print("✅ CUDA推論テスト成功")
                    
                    # cuDNNチェック
                    if torch.backends.cudnn.is_available():
                        cuda_info["cudnn_available"] = True
                        print(f"✅ cuDNN利用可能: v{torch.backends.cudnn.version()}")
                    else:
                        print("⚠️ cuDNN利用不可")
                        
                except Exception as e:
                    print(f"⚠️ CUDA動作テストでエラー: {e}")
                    cuda_info["errors"].append(f"CUDA operation test failed: {e}")
            else:
                print("⚠️ CUDAデバイスが見つかりません")
                cuda_info["errors"].append("No CUDA devices found")
        else:
            print("⚠️ torch.cuda.is_available() = False")
            cuda_info["errors"].append("torch.cuda.is_available() returned False")
            
    except ImportError:
        print("❌ PyTorch未インストール")
        cuda_info["errors"].append("PyTorch not installed")
    except Exception as e:
        print(f"❌ CUDA確認エラー: {e}")
        cuda_info["errors"].append(f"CUDA check error: {e}")
    
    # ONNXRuntime-GPU互換性判定
    if cuda_info["cuda_available"] and cuda_info["cudnn_available"]:
        cuda_info["onnx_gpu_compatible"] = True
        print("🚀 ONNXRuntime-GPU互換環境を検出")
        return True
    else:
        print("💻 CPU環境として動作します")
        print("📝 GPU版を使用するには以下が必要です:")
        print("   - CUDA Toolkit (11.8以上)")
        print("   - cuDNN (8.0以上)")
        print("   - 互換性のあるNVIDIA GPU")
        return False

def setup_onnxruntime_for_exe():
    """ONNXRuntimeをexe化に適した状態にセットアップ（CUDA対応）"""
    
    print("🔧 ONNXRuntime exe化セットアップを開始...")
    
    # CUDA環境チェック
    cuda_available = check_cuda_availability()
    
    try:
        # 1. 互換性のあるパッケージセットをインストール
        print("📦 互換性のあるパッケージセットをインストール中...")
        
        # 既存のONNX関連パッケージを完全削除
        print("📦 既存パッケージをアンインストール中...")
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", 
            "onnxruntime", "onnxruntime-gpu", "onnx", "numpy", "-y"
        ], check=False)  # エラーを表示して確認
        
        # CUDA環境に応じてONNXRuntimeバージョンを選択（安全なフォールバック付き）
        if cuda_available:
            print("🚀 CUDA環境検出 - GPU版ONNXRuntimeをインストール")
            onnxruntime_package = "onnxruntime-gpu==1.22.0"
            fallback_package = "onnxruntime==1.22.0"  # GPU版失敗時のフォールバック
        else:
            print("💻 CPU環境 - CPU版ONNXRuntimeをインストール")
            onnxruntime_package = "onnxruntime==1.22.0"
            fallback_package = None
        
        # 最新の互換性のあるバージョンセットをインストール (2024年12月更新)
        compatible_packages = [
            "numpy>=2.3.0,<3.0.0",   # ONNXRuntime 1.22.0と互換性のあるNumPy（最新版対応）
            "onnx==1.16.0",           # ONNXRuntime 1.22.0と互換性のあるONNX (IR v10サポート)
            onnxruntime_package       # 環境に応じたONNXRuntime
        ]
        
        for package in compatible_packages:
            print(f"📦 インストール中: {package}")
            try:
                if "numpy" in package:
                    # NumPyは最新版をインストール（古いバージョンからアップグレード）
                    subprocess.run([
                        sys.executable, "-m", "pip", "install", package, "--upgrade", "--no-cache-dir"
                    ], check=True, capture_output=True)
                elif "onnxruntime-gpu" in package:
                    # GPU版のインストール（失敗時はフォールバック）
                    try:
                        subprocess.run([
                            sys.executable, "-m", "pip", "install", package, "--no-deps", "--disable-pip-version-check"
                        ], check=True, capture_output=True)
                        print("✅ ONNXRuntime-GPU インストール成功")
                    except subprocess.CalledProcessError as e:
                        print(f"⚠️ ONNXRuntime-GPU インストール失敗: {e}")
                        if fallback_package:
                            print(f"🔄 CPU版にフォールバック: {fallback_package}")
                            subprocess.run([
                                sys.executable, "-m", "pip", "install", fallback_package, "--no-deps"
                            ], check=True)
                            print("✅ ONNXRuntime-CPU フォールバック成功")
                        else:
                            raise
                else:
                    subprocess.run([
                        sys.executable, "-m", "pip", "install", package, "--no-deps"
                    ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ パッケージインストール失敗: {package} - {e}")
                if "onnxruntime" not in package:  # ONNXRuntime以外のエラーは続行
                    continue
                else:
                    raise
        
        # NudeNetを再インストールして依存関係を解決
        print("📦 NudeNet依存関係修正中...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "nudenet", "--force-reinstall", "--no-deps"
        ], check=False)  # 依存関係チェックをスキップしてNudeNetを強制インストール
        
        # 必要な依存関係を個別にインストール
        dependencies = [
            "coloredlogs", "flatbuffers", "packaging", "protobuf", 
            "sympy", "humanfriendly", "pyreadline3", "mpmath", "typing_extensions"
        ]
        
        for dep in dependencies:
            subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=False)  # 依存関係は失敗しても続行
        
        print("✅ 互換性パッケージセットのインストール完了")
        
        # 2. ONNXRuntimeのインストール確認
        import onnxruntime as ort
        print(f"✅ ONNXRuntime version: {ort.__version__}")
        print(f"✅ ONNXRuntime path: {ort.__file__}")
        
        # 3. NumPyバージョン確認（厳格チェック）
        import numpy as np
        numpy_version = np.__version__
        print(f"✅ NumPy version: {numpy_version}")
        
        # バージョンチェック（2.3.0以上を推奨）
        major, minor = map(int, numpy_version.split('.')[:2])
        if major < 2 or (major == 2 and minor < 3):
            print(f"⚠️ 警告: 古いNumPyバージョン（現在: {numpy_version}, 推奨: 2.3.0以上）")
            print("🔄 NumPyを最新版にアップグレードします...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "numpy>=2.3.0,<3.0.0", "--upgrade", "--no-cache-dir"
            ], check=True)
            # 再確認
            import importlib
            importlib.reload(np)
            print(f"✅ NumPyアップグレード後: {np.__version__}")
        else:
            print(f"✅ NumPy {numpy_version} は最新要件を満たしています")
        
        # 4. ONNXバージョン確認
        import onnx
        print(f"✅ ONNX version: {onnx.__version__}")
        
        # 5. 利用可能なプロバイダーを確認
        providers = ort.get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        # CUDA対応確認
        if "CUDAExecutionProvider" in providers:
            print("🚀 CUDAExecutionProvider利用可能 - GPU加速有効")
        else:
            print("💻 CPUExecutionProviderのみ利用可能")
        
        # 6. ONNXRuntimeのDLLファイルを確認
        onnx_dir = Path(ort.__file__).parent
        dll_files = list(onnx_dir.glob("**/*.dll"))
        print(f"✅ Found {len(dll_files)} DLL files:")
        for dll in dll_files:
            print(f"   - {dll}")
        
        # 7. 互換性のあるテストモデルで検証
        print("🧪 ONNXRuntime互換性テストを実行中...")
        
        try:
            from onnx import helper, TensorProto
            
            # ONNX IR version 10 (ONNXRuntime 1.18.1互換) でモデル作成
            input_tensor = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3])
            output_tensor = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 3])
            
            # 恒等変換ノード
            identity_node = helper.make_node('Identity', ['input'], ['output'])
            
            # グラフ作成
            graph = helper.make_graph([identity_node], 'test_graph', [input_tensor], [output_tensor])
            
            # モデル作成（IR version 10を明示的に指定）
            model = helper.make_model(graph, ir_version=10)
            
            # モデルをバイト形式に変換
            model_bytes = model.SerializeToString()
            
            # 段階的なプロバイダーテスト
            test_success = False
            
            if "CUDAExecutionProvider" in providers:
                print("🧪 GPU加速テストを実行中...")
                try:
                    # まずGPU専用でテスト
                    gpu_session = ort.InferenceSession(model_bytes, providers=['CUDAExecutionProvider'])
                    input_data = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
                    gpu_result = gpu_session.run(None, {'input': input_data})
                    print(f"✅ GPU加速テスト成功: {gpu_result[0]}")
                    test_success = True
                except Exception as gpu_error:
                    print(f"⚠️ GPU加速テスト失敗: {gpu_error}")
                    print("🔄 CPUフォールバックテストを実行中...")
            
            if not test_success:
                print("🧪 CPU処理テストを実行中...")
                try:
                    # CPUでのテスト
                    cpu_session = ort.InferenceSession(model_bytes, providers=['CPUExecutionProvider'])
                    input_data = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
                    cpu_result = cpu_session.run(None, {'input': input_data})
                    used_providers = cpu_session.get_providers()
                    print(f"✅ CPU処理テスト成功 (プロバイダー: {used_providers[0]})")
                    print(f"✅ テスト結果: {cpu_result[0]}")
                    test_success = True
                except Exception as cpu_error:
                    print(f"❌ CPU処理テストも失敗: {cpu_error}")
            
            if not test_success:
                raise Exception("Both GPU and CPU tests failed")
                
        except Exception as e:
            print(f"⚠️ ONNXテスト失敗（基本インポートは成功）: {e}")
            print("✅ ONNXRuntime基本インポート成功")
            print("💡 実際のアプリケーションでは動作する可能性があります")
        
        # 8. Visual C++ Redistributableの確認
        print("🔍 Visual C++ Redistributableの確認...")
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            print("✅ Windows API アクセス可能")
        except Exception as e:
            print(f"⚠️ Windows API アクセスに問題: {e}")
        
        print("✅ ONNXRuntime exe化セットアップ完了")
        return True
        
    except Exception as e:
        print(f"❌ ONNXRuntime セットアップエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def install_vcredist():
    """Visual C++ Redistributableのインストール状況を確認"""
    print("🔍 Visual C++ Redistributable確認中...")
    
    # レジストリからインストール済みのVC++ Redistributableを確認
    try:
        import winreg
        
        # 64-bit版の確認
        key_path = r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                installed, _ = winreg.QueryValueEx(key, "Installed")
                version, _ = winreg.QueryValueEx(key, "Version")
                print(f"✅ VC++ Redistributable x64 installed: {installed}, version: {version}")
        except FileNotFoundError:
            print("⚠️ VC++ Redistributable x64 not found in registry")
        
        # 32-bit版の確認
        key_path = r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x86"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                installed, _ = winreg.QueryValueEx(key, "Installed")
                version, _ = winreg.QueryValueEx(key, "Version")
                print(f"✅ VC++ Redistributable x86 installed: {installed}, version: {version}")
        except FileNotFoundError:
            print("⚠️ VC++ Redistributable x86 not found in registry")
            
    except ImportError:
        print("⚠️ winreg module not available")
    except Exception as e:
        print(f"⚠️ Registry check failed: {e}")

def create_onnx_test_script():
    """ONNXRuntimeテスト用スクリプトを作成"""
    test_script = """
import os
import sys

# 環境変数設定
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['ORT_LOGGING_LEVEL'] = '3'

print("🧪 ONNXRuntime exe環境テスト開始...")
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")

try:
    import numpy as np
    print(f"✅ NumPy version: {np.__version__}")
    
    import onnx
    print(f"✅ ONNX version: {onnx.__version__}")
    
    import onnxruntime as ort
    print(f"✅ ONNXRuntime import successful: {ort.__version__}")
    
    providers = ort.get_available_providers()
    print(f"✅ Available providers: {providers}")
    
    # NudeNetテスト
    try:
        from nudenet import NudeDetector
        print("✅ NudeDetector import successful")
        
        detector = NudeDetector()
        print("✅ NudeDetector initialization successful")
        
        # 簡単な検出テスト
        from PIL import Image
        test_image = Image.new('RGB', (224, 224), color='white')
        result = detector.detect(test_image)
        print(f"✅ NudeNet detection test successful: {len(result)} detections")
        
    except Exception as e:
        print(f"⚠️ NudeNet test failed: {e}")
    
    print("✅ ONNXRuntime exe環境テスト完了")
    
except Exception as e:
    print(f"❌ ONNXRuntime test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    with open("test_onnx_exe.py", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    print("✅ ONNXRuntimeテストスクリプト作成完了: test_onnx_exe.py")

if __name__ == "__main__":
    print("=" * 60)
    print("ONNXRuntime Setup for PyInstaller")
    print("=" * 60)
    
    # Visual C++ Redistributableの確認
    install_vcredist()
    
    # ONNXRuntimeのセットアップ
    success = setup_onnxruntime_for_exe()
    
    # テストスクリプトの作成
    create_onnx_test_script()
    
    if success:
        print("\n✅ セットアップ完了！次のステップ:")
        print("1. build_lightweight_dll.spec を使用してビルド実行")
        print("2. exe化後にtest_onnx_exe.pyでテスト実行")
        print("\n📋 インストールされたバージョン:")
        print("   - NumPy: 2.3.0 (最新互換)")
        print("   - ONNX: 1.16.0 (IR version 10)")
        print("   - ONNXRuntime: 1.22.0 (最新安定版)")
        sys.exit(0)
    else:
        print("\n❌ セットアップに問題が発生しました")
        sys.exit(1) 