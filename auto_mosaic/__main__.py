#!/usr/bin/env python3
"""
自動モザエセ v1.0 - メインエントリーポイント

使用方法:
    python -m auto_mosaic                    # 通常起動
    python -m auto_mosaic --setup            # 初回セットアップダイアログを強制表示
    python -m auto_mosaic --first-run        # 初回セットアップダイアログを強制表示
    python -m auto_mosaic --help             # ヘルプ表示
"""

import sys
import argparse
from pathlib import Path
import os

def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        prog="auto_mosaic",
        description="自動モザエセ v1.0 - アニメ・イラスト画像の男女局部モザイク処理ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m auto_mosaic                    通常起動
  python -m auto_mosaic --setup            初回セットアップダイアログを表示
  python -m auto_mosaic --first-run        初回セットアップダイアログを表示

機能:
  • YOLO検出 + SAMセグメンテーション
  • 高精度な局部検出とモザイク処理
  • FANZA基準対応
  • シームレス処理
        """
    )
    
    parser.add_argument(
        "--setup", "--first-run",
        action="store_true",
        dest="show_setup",
        help="初回セットアップダイアログを強制表示"
    )
    
    parser.add_argument(
        "--test-onnx",
        action="store_true",
        dest="test_onnx",
        help="ONNXRuntimeの動作テストを実行（exe環境用）"
    )
    
    parser.add_argument(
        "--test-nudenet",
        action="store_true",
        dest="test_nudenet", 
        help="NudeNetの機能テストを実行（exe環境用）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="自動モザエセ v1.0.0"
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    # exe環境でのDLL問題を早期に修正
    if getattr(sys, 'frozen', False):
        import ctypes
        import platform
        
        # Windows DLL読み込み問題を修正
        if platform.system() == 'Windows' and hasattr(sys, '_MEIPASS'):
            dll_dir = sys._MEIPASS
            try:
                # Windows DLL検索パスを設定
                ctypes.windll.kernel32.SetDllDirectoryW(dll_dir)
                try:
                    ctypes.windll.kernel32.AddDllDirectory(dll_dir)
                except AttributeError:
                    pass  # Windows 7未満では利用できない
            except Exception:
                pass  # DLL操作に失敗した場合は無視
            
            # DLLパスをPATHに追加
            current_path = os.environ.get('PATH', '')
            if dll_dir not in current_path:
                os.environ['PATH'] = dll_dir + os.pathsep + current_path
        
        # ONNX Runtime環境変数を設定
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['ORT_LOGGING_LEVEL'] = '3'
        os.environ['ORT_PROVIDERS'] = 'CPUExecutionProvider'
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

    args = parse_args()
    
    # utils.pyの関数をインポート（循環インポート回避のため遅延インポート）
    from auto_mosaic.src.utils import is_developer_mode
    
    # 開発者モード時のみデバッグ情報を出力
    if is_developer_mode():
        print(f"🚀 自動モザエセ起動中...")
        print(f"📍 実行環境: {'exe' if getattr(sys, 'frozen', False) else 'development'}")
        print(f"📁 実行パス: {sys.executable}")
        if hasattr(sys, '_MEIPASS'):
            print(f"📦 一時展開パス: {sys._MEIPASS}")
    
    try:
        if args.test_onnx:
            # ONNXRuntimeテスト専用モード（開発者モード時のみ詳細出力）
            dev_mode = is_developer_mode()
            if dev_mode:
                print("\n🔬 ONNXRuntime単体テストを実行中...")
            try:
                # 環境変数設定
                os.environ['OMP_NUM_THREADS'] = '1'
                os.environ['ORT_LOGGING_LEVEL'] = '3'
                
                import onnxruntime as ort
                if dev_mode:
                    print(f"✅ ONNXRuntime import successful: {ort.__version__}")
                    print(f"✅ ONNXRuntime path: {ort.__file__}")
                
                providers = ort.get_available_providers()
                if dev_mode:
                    print(f"✅ Available providers: {providers}")
                
                # 簡単なセッション作成テスト
                session = ort.InferenceSession(None, providers=['CPUExecutionProvider'])
                if dev_mode:
                    print("✅ ONNXRuntime session creation successful")
                
                # NudeNetテスト
                from nudenet import NudeDetector
                if dev_mode:
                    print("✅ NudeDetector import successful")
                
                detector = NudeDetector()
                if dev_mode:
                    print("✅ NudeDetector initialization successful")
                    print("🎉 すべてのONNXRuntimeテスト成功！")
                return
                
            except Exception as e:
                if dev_mode:
                    print(f"❌ ONNXRuntimeテスト失敗: {e}")
                    import traceback
                    traceback.print_exc()
                return
        
        elif args.test_nudenet:
            # NudeNet機能テスト専用モード（開発者モード時のみ詳細出力）
            dev_mode = is_developer_mode()
            if dev_mode:
                print("\n🔬 NudeNet機能テストを実行中...")
            try:
                # 環境変数設定
                os.environ['OMP_NUM_THREADS'] = '1'
                os.environ['ORT_LOGGING_LEVEL'] = '3'
                
                if dev_mode:
                    print("📦 モジュールインポートテスト...")
                import nudenet
                if dev_mode:
                    print(f"✅ NudeNet import successful: {getattr(nudenet, '__version__', 'unknown')}")
                    print(f"✅ NudeNet path: {nudenet.__file__}")
                
                from nudenet import NudeDetector
                if dev_mode:
                    print("✅ NudeDetector class import successful")
                    print("🔧 NudeDetector初期化テスト...")
                detector = NudeDetector()
                if dev_mode:
                    print("✅ NudeDetector initialization successful")
                    print("🖼️ テスト画像での検出テスト...")
                
                from PIL import Image
                import numpy as np
                
                # 64x64のテスト画像を作成（NumPy配列として）
                test_image_pil = Image.new('RGB', (64, 64), color='white')
                test_image = np.array(test_image_pil)
                if dev_mode:
                    print(f"✅ Test image created: {test_image.shape}")
                
                # 検出実行
                result = detector.detect(test_image)
                if dev_mode:
                    print(f"✅ NudeNet detection successful: {len(result)} detections found")
                    
                    # 結果の詳細表示
                    if result:
                        for i, detection in enumerate(result):
                            print(f"  Detection {i+1}: {detection}")
                    else:
                        print("  No detections found (expected for white test image)")
                    
                    print("🎉 NudeNet機能テスト完全成功！")
                return
                
            except Exception as e:
                if dev_mode:
                    print(f"❌ NudeNet機能テスト失敗: {e}")
                    import traceback
                    traceback.print_exc()
                return
        
        elif args.show_setup:
            # 初回セットアップダイアログを強制表示するため、
            # 一時的にマーカーファイルを移動して初回起動状態にする
            dev_mode = is_developer_mode()
            if dev_mode:
                print("🔄 初回セットアップを強制実行します...")
            
            from auto_mosaic.src.utils import get_app_data_dir
            import shutil
            
            marker_file = get_app_data_dir() / "config" / "first_run_complete"
            backup_file = get_app_data_dir() / "config" / "first_run_complete.backup"
            
            # マーカーファイルが存在する場合は一時的にバックアップ
            marker_existed = False
            if marker_file.exists():
                marker_existed = True
                shutil.move(str(marker_file), str(backup_file))
                if dev_mode:
                    print("📝 既存のセットアップ完了マーカーを一時的にバックアップしました")
            
            try:
                # 通常のGUIアプリケーションを起動（初回起動として動作）
                from auto_mosaic.src.gui import main as gui_main
                gui_main()
            finally:
                # バックアップを復元
                if marker_existed and backup_file.exists():
                    shutil.move(str(backup_file), str(marker_file))
                    if dev_mode:
                        print("🔄 セットアップ完了マーカーを復元しました")
            
        else:
            # exe環境でのNudeNetテスト（開発者モード時のみ）
            dev_mode = is_developer_mode()
            if getattr(sys, 'frozen', False) and dev_mode:
                print("\n🔬 exe環境でのNudeNetテストを実行中...")
                try:
                    # DLL パスの追加設定
                    if hasattr(sys, '_MEIPASS'):
                        dll_path = sys._MEIPASS
                        current_path = os.environ.get('PATH', '')
                        if dll_path not in current_path:
                            os.environ['PATH'] = dll_path + os.pathsep + current_path
                        print(f"🔧 DLLパス追加: {dll_path}")
                    
                    # ONNX Runtime の環境変数を設定
                    os.environ['OMP_NUM_THREADS'] = '1'
                    os.environ['ORT_LOGGING_LEVEL'] = '3'
                    os.environ['ORT_PROVIDERS'] = 'CPUExecutionProvider'
                    print("🔧 ONNX Runtime環境変数設定完了")
                    
                    # 最初にONNXRuntimeを直接テスト
                    print("📦 ONNXRuntime直接テスト...")
                    try:
                        import onnxruntime as ort
                        print(f"✅ ONNXRuntime import successful: {ort.__version__}")
                        
                        # プロバイダー確認
                        providers = ort.get_available_providers()
                        print(f"✅ Available providers: {providers}")
                    except ImportError as ort_import_e:
                        print(f"❌ ONNXRuntime import failed: {ort_import_e}")
                        print("🔄 Skipping NudeNet test due to ONNXRuntime import issues")
                        print("📝 This is expected in some exe environments - the app will work with anime models only")
                        return
                    
                    print("📦 NudeNetモジュールテスト...")
                    import nudenet
                    print(f"✅ NudeNet import successful: {getattr(nudenet, '__version__', 'unknown')}")
                    
                    from nudenet import NudeDetector
                    print("✅ NudeDetector class import successful")
                    
                    print("🔧 NudeDetector初期化中...")
                    detector = NudeDetector()
                    print("✅ NudeDetector initialization successful")
                    
                    from PIL import Image
                    import numpy as np
                    
                    # NumPy配列として作成（NudeNetが期待する形式）
                    test_image_pil = Image.new('RGB', (64, 64), color='white')
                    test_image = np.array(test_image_pil)
                    result = detector.detect(test_image)
                    print(f"✅ NudeNet detection test successful: {len(result)} detections")
                    
                    print("🎉 NudeNet is fully functional in exe environment!")
                    
                except Exception as e:
                    print(f"❌ NudeNet test failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 通常のGUIアプリケーション起動
            from auto_mosaic.src.gui import main as gui_main
            gui_main()
            
    except KeyboardInterrupt:
        if is_developer_mode():
            print("\n⚠️ ユーザーによって中断されました")
    except Exception as e:
        # 開発者モード時はコンソールに表示
        if is_developer_mode():
            print(f"❌ エラーが発生しました: {str(e)}")
            import traceback
            traceback.print_exc()
        else:
            # 配布版では一時的にエラーログファイルを作成
            try:
                import tempfile
                import traceback
                from datetime import datetime
                
                # 一時ディレクトリにエラーログを作成
                log_dir = Path(tempfile.gettempdir()) / "auto_mosaic_debug"
                log_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = log_dir / f"error_log_{timestamp}.txt"
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"自動モザエセ エラーログ\n")
                    f.write(f"発生時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"実行環境: {'exe' if getattr(sys, 'frozen', False) else 'development'}\n")
                    f.write(f"実行パス: {sys.executable}\n")
                    if hasattr(sys, '_MEIPASS'):
                        f.write(f"一時展開パス: {sys._MEIPASS}\n")
                    f.write(f"\n--- エラー詳細 ---\n")
                    f.write(f"エラー: {str(e)}\n\n")
                    f.write("--- スタックトレース ---\n")
                    f.write(traceback.format_exc())
                
                # エラーメッセージをコンソールに表示（配布版でも表示）
                print(f"❌ エラーが発生しました: {str(e)}")
                print(f"📄 詳細なエラーログが保存されました: {log_file}")
                print("このファイルを開発者に送信してください。")
                print("何かキーを押してください...")
                input()
                
            except Exception as log_error:
                # ログ作成に失敗した場合は基本的なエラーメッセージのみ表示
                print(f"❌ エラーが発生しました: {str(e)}")
                print(f"⚠️ ログファイルの作成に失敗しました: {str(log_error)}")
                print("何かキーを押してください...")
                input()

if __name__ == "__main__":
    main() 