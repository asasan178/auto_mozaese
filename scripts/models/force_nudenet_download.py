#!/usr/bin/env python3
"""
NudeNetのモデルファイルを強制的にダウンロードして正しい場所を特定するスクリプト
"""

import os
import shutil
import site
from pathlib import Path
import tempfile

def force_download_nudenet_models():
    """NudeNetのモデルを強制的にダウンロード"""
    print("=== NudeNetモデルのダウンロード開始 ===")
    
    # 既存のNudeNetキャッシュをクリア
    home_dir = Path.home()
    nudenet_cache = home_dir / ".nudenet"
    
    if nudenet_cache.exists():
        print(f"既存のキャッシュを削除: {nudenet_cache}")
        shutil.rmtree(nudenet_cache)
    
    # NudeNetを初期化してモデルをダウンロード
    print("NudeDetectorを初期化中...")
    from nudenet import NudeDetector
    
    detector = NudeDetector()
    print("✅ NudeDetector初期化完了")
    
    # ダウンロードされたモデルファイルを探す
    print("\n=== ダウンロードされたモデルファイルを探索 ===")
    
    # site-packagesのnudenetフォルダを確認
    for site_dir in site.getsitepackages():
        nudenet_pkg = Path(site_dir) / "nudenet"
        if nudenet_pkg.exists():
            print(f"site-packages nudenet: {nudenet_pkg}")
            for onnx_file in nudenet_pkg.rglob("*.onnx"):
                size = onnx_file.stat().st_size
                print(f"  {onnx_file.name}: {size/1024/1024:.2f} MB")
    
    # ホームディレクトリの.nudenetを確認
    if nudenet_cache.exists():
        print(f"ユーザーキャッシュ: {nudenet_cache}")
        for onnx_file in nudenet_cache.rglob("*.onnx"):
            size = onnx_file.stat().st_size
            print(f"  {onnx_file.name}: {size/1024/1024:.2f} MB")
    
    # 現在のディレクトリにコピー
    copy_models_to_project()
    
    # 簡単なテストを実行
    test_nudenet_detection(detector)

def copy_models_to_project():
    """見つかったモデルファイルをプロジェクトディレクトリにコピー"""
    print("\n=== プロジェクトディレクトリへのコピー ===")
    
    project_models_dir = Path("nudenet_models")
    project_models_dir.mkdir(exist_ok=True)
    
    copied_files = []
    
    # site-packagesから探す
    for site_dir in site.getsitepackages():
        nudenet_pkg = Path(site_dir) / "nudenet"
        if nudenet_pkg.exists():
            for onnx_file in nudenet_pkg.rglob("*.onnx"):
                if onnx_file.stat().st_size > 1024:  # 1KB以上のファイルのみ
                    dest = project_models_dir / onnx_file.name
                    try:
                        shutil.copy2(onnx_file, dest)
                        size = dest.stat().st_size
                        print(f"コピー完了: {onnx_file.name} ({size/1024/1024:.2f} MB)")
                        copied_files.append(dest)
                    except Exception as e:
                        print(f"コピー失敗: {onnx_file.name} - {e}")
    
    # ホームディレクトリから探す
    home_dir = Path.home()
    nudenet_cache = home_dir / ".nudenet"
    if nudenet_cache.exists():
        for onnx_file in nudenet_cache.rglob("*.onnx"):
            if onnx_file.stat().st_size > 1024:  # 1KB以上のファイルのみ
                dest = project_models_dir / onnx_file.name
                if not dest.exists():  # まだコピーされていない場合のみ
                    try:
                        shutil.copy2(onnx_file, dest)
                        size = dest.stat().st_size
                        print(f"コピー完了: {onnx_file.name} ({size/1024/1024:.2f} MB)")
                        copied_files.append(dest)
                    except Exception as e:
                        print(f"コピー失敗: {onnx_file.name} - {e}")
    
    print(f"\n合計 {len(copied_files)} 個のファイルをコピーしました")
    return copied_files

def test_nudenet_detection(detector):
    """NudeNetの動作テスト"""
    print("\n=== NudeNet動作テスト ===")
    
    try:
        from PIL import Image
        import numpy as np
        
        # テスト用の白い画像を作成
        test_image = Image.new('RGB', (224, 224), color='white')
        
        # 検出テスト
        result = detector.detect(test_image)
        print(f"✅ 検出テスト成功: {len(result)} 個の検出結果")
        
        # 分類テスト（可能であれば）
        try:
            classification = detector.classify(test_image)
            print(f"✅ 分類テスト成功: {classification}")
        except Exception as e:
            print(f"分類テスト: {e}")
            
    except Exception as e:
        print(f"❌ 動作テスト失敗: {e}")

if __name__ == "__main__":
    force_download_nudenet_models() 