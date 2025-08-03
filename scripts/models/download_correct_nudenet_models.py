#!/usr/bin/env python3
"""
正しいNudeNetモデルファイルをダウンロードするスクリプト
"""

import os
import requests
import shutil
from pathlib import Path

def download_file(url, destination):
    """ファイルをダウンロードする"""
    print(f"ダウンロード中: {url}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    file_size = os.path.getsize(destination)
    print(f"ダウンロード完了: {destination} ({file_size/1024/1024:.2f} MB)")
    return file_size

def main():
    # nudenet_modelsディレクトリを作成
    models_dir = Path("nudenet_models")
    models_dir.mkdir(exist_ok=True)
    
    # HuggingFaceからNudeNetモデルをダウンロード
    base_url = "https://huggingface.co/notai-tech/nudenet_classifier_model_v3/resolve/main"
    
    models_to_download = [
        {
            "filename": "detector_v2_default_checkpoint.onnx",
            "url": f"{base_url}/detector_v2_default_checkpoint.onnx",
            "expected_min_size": 10 * 1024 * 1024  # 最低10MB期待
        },
        {
            "filename": "classifier_model.onnx", 
            "url": f"{base_url}/classifier_model.onnx",
            "expected_min_size": 10 * 1024 * 1024  # 最低10MB期待
        }
    ]
    
    # 320n.onnxは既に正しくダウンロードされているかチェック
    onnx_320n = models_dir / "320n.onnx"
    if onnx_320n.exists():
        size = onnx_320n.stat().st_size
        print(f"320n.onnx: {size/1024/1024:.2f} MB (既存)")
        if size < 10 * 1024 * 1024:  # 10MB未満の場合は再ダウンロード
            print("320n.onnxが小さすぎます。再ダウンロードします。")
            models_to_download.append({
                "filename": "320n.onnx",
                "url": "https://huggingface.co/notai-tech/yolov8n_nudenet/resolve/main/320n.onnx",
                "expected_min_size": 10 * 1024 * 1024
            })
    else:
        models_to_download.append({
            "filename": "320n.onnx", 
            "url": "https://huggingface.co/notai-tech/yolov8n_nudenet/resolve/main/320n.onnx",
            "expected_min_size": 10 * 1024 * 1024
        })
    
    # nms-yolov8.onnxも追加（小さいファイルだが念のため）
    nms_file = models_dir / "nms-yolov8.onnx"
    if not nms_file.exists() or nms_file.stat().st_size < 1024:
        models_to_download.append({
            "filename": "nms-yolov8.onnx",
            "url": "https://huggingface.co/notai-tech/yolov8n_nudenet/resolve/main/nms-yolov8.onnx", 
            "expected_min_size": 1024  # 1KB以上
        })
    
    # ダウンロード実行
    for model in models_to_download:
        destination = models_dir / model["filename"]
        
        # 既存の小さなファイルがあれば削除
        if destination.exists():
            current_size = destination.stat().st_size
            if current_size < model["expected_min_size"]:
                print(f"小さすぎるファイルを削除: {destination} ({current_size} bytes)")
                destination.unlink()
        
        try:
            actual_size = download_file(model["url"], destination)
            
            if actual_size < model["expected_min_size"]:
                print(f"⚠️ 警告: {model['filename']} のサイズが期待値より小さいです ({actual_size} bytes)")
            else:
                print(f"✅ {model['filename']} のダウンロードが成功しました")
                
        except Exception as e:
            print(f"❌ {model['filename']} のダウンロードに失敗: {e}")
    
    # 最終確認
    print("\n=== 最終確認 ===")
    for file in models_dir.glob("*.onnx"):
        size = file.stat().st_size
        print(f"{file.name}: {size/1024/1024:.2f} MB")

if __name__ == "__main__":
    main() 