#!/usr/bin/env python3
"""
NudeNetモデルファイル抽出スクリプト
HuggingFace Hubからダウンロードされたモデルファイルをnudenet_modelsフォルダにコピー
"""

import os
import shutil
import sys
from pathlib import Path

def find_and_copy_nudenet_models():
    """NudeNetモデルファイルを見つけてnudenet_modelsフォルダにコピー"""
    
    # nudenet_modelsディレクトリを作成
    models_dir = Path("nudenet_models")
    models_dir.mkdir(exist_ok=True)
    print(f"📁 Models directory: {models_dir.absolute()}")
    
    # NudeDetectorを初期化してモデルをダウンロード
    print("🔍 Initializing NudeDetector to ensure models are downloaded...")
    try:
        from nudenet import NudeDetector
        import numpy as np
        
        # モデルを初期化（自動ダウンロード）
        detector = NudeDetector()
        
        # テスト実行してモデルファイルを確実にダウンロード
        test_img = np.random.randint(0, 255, (320, 320, 3), dtype=np.uint8)
        _ = detector.detect(test_img)
        print("✅ NudeDetector test completed - models should be downloaded")
        
    except Exception as e:
        print(f"❌ Error initializing NudeDetector: {e}")
        return False
    
    # HuggingFace Hub Cache からモデルファイルを探す
    cache_dirs = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".cache" / "huggingface",
        Path.home() / ".huggingface" / "hub",
    ]
    
    found_models = []
    target_files = ["320n.onnx", "nms-yolov8.onnx", "detector_v2_default_checkpoint.onnx", "classifier_model.onnx"]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            print(f"🔍 Searching in: {cache_dir}")
            
            # すべてのサブディレクトリを検索
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    if file in target_files or file.endswith('.onnx'):
                        file_path = Path(root) / file
                        print(f"📦 Found model file: {file_path}")
                        found_models.append((file, file_path))
    
    # モデルファイルをコピー
    copied_count = 0
    for filename, source_path in found_models:
        target_path = models_dir / filename
        
        if not target_path.exists() or target_path.stat().st_size != source_path.stat().st_size:
            try:
                shutil.copy2(source_path, target_path)
                print(f"✅ Copied: {filename} -> {target_path}")
                copied_count += 1
            except Exception as e:
                print(f"❌ Failed to copy {filename}: {e}")
        else:
            print(f"⏭️ Already exists: {filename}")
    
    # 最低限必要な320n.onnxを作成
    detector_files = [f for f in models_dir.glob("*detector*.onnx")]
    target_320n = models_dir / "320n.onnx"
    
    if not target_320n.exists() and detector_files:
        try:
            shutil.copy2(detector_files[0], target_320n)
            print(f"✅ Created 320n.onnx from {detector_files[0].name}")
            copied_count += 1
        except Exception as e:
            print(f"❌ Failed to create 320n.onnx: {e}")
    
    # NMS YOLOv8ファイルをHuggingFaceから直接ダウンロード
    try:
        from huggingface_hub import hf_hub_download
        
        nms_file = models_dir / "nms-yolov8.onnx"
        if not nms_file.exists():
            print("📥 Downloading nms-yolov8.onnx from HuggingFace...")
            downloaded_file = hf_hub_download(
                repo_id="deepghs/nudenet_onnx",
                filename="nms-yolov8.onnx",
                local_dir=str(models_dir),
                local_dir_use_symlinks=False
            )
            print(f"✅ Downloaded: {downloaded_file}")
            copied_count += 1
            
        # 320n.onnxもダウンロード
        onnx_320n = models_dir / "320n.onnx"
        if not onnx_320n.exists():
            print("📥 Downloading 320n.onnx from HuggingFace...")
            downloaded_file = hf_hub_download(
                repo_id="deepghs/nudenet_onnx", 
                filename="320n.onnx",
                local_dir=str(models_dir),
                local_dir_use_symlinks=False
            )
            print(f"✅ Downloaded: {downloaded_file}")
            copied_count += 1
            
    except Exception as e:
        print(f"⚠️ HuggingFace download failed: {e}")
    
    # 結果確認
    final_files = list(models_dir.glob("*.onnx"))
    print(f"\n📊 Final result:")
    print(f"   Copied/Downloaded: {copied_count} files")
    print(f"   Total ONNX files: {len(final_files)}")
    
    for file in final_files:
        size_mb = file.stat().st_size / (1024*1024)
        print(f"   📄 {file.name} ({size_mb:.1f} MB)")
    
    return len(final_files) > 0

if __name__ == "__main__":
    success = find_and_copy_nudenet_models()
    if success:
        print("\n🎉 NudeNet models extraction completed successfully!")
    else:
        print("\n❌ NudeNet models extraction failed!")
        sys.exit(1) 