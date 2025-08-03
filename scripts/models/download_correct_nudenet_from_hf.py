#!/usr/bin/env python3
"""
HuggingFaceから正しいNudeNetモデルファイルをダウンロードするスクリプト
"""

import os
import requests
from pathlib import Path

def download_file_with_progress(url, destination):
    """プログレスバー付きでファイルをダウンロード"""
    print(f"ダウンロード開始: {url}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0
    
    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                
                # プログレス表示
                if total_size > 0:
                    progress = (downloaded_size / total_size) * 100
                    print(f"\r進行状況: {progress:.1f}% ({downloaded_size/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)", end='')
    
    print()  # 改行
    file_size = os.path.getsize(destination)
    print(f"ダウンロード完了: {destination} ({file_size/1024/1024:.2f} MB)")
    return file_size

def main():
    # nudenet_modelsディレクトリを準備
    models_dir = Path("nudenet_models")
    models_dir.mkdir(exist_ok=True)
    
    # HuggingFaceの正しいNudeNetモデルURL
    base_url = "https://huggingface.co/gqfwqgw/NudeNet_classifier_model/resolve/d9606abb0e0260c99765e09360df4e26d81ee794"
    
    models_to_download = [
        {
            "filename": "classifier_model.onnx",
            "url": f"{base_url}/classifier_model.onnx",
            "expected_size": 83.6 * 1024 * 1024  # 83.6MB
        },
        {
            "filename": "detector_v2_default_checkpoint.onnx", 
            "url": f"{base_url}/detector_v2_default_checkpoint.onnx",
            "expected_size": 147 * 1024 * 1024  # 147MB
        }
    ]
    
    print("=== 正しいNudeNetモデルファイルのダウンロード ===")
    
    for model in models_to_download:
        destination = models_dir / model["filename"]
        
        # 既存のファイルをチェック
        if destination.exists():
            current_size = destination.stat().st_size
            expected_size = model["expected_size"]
            
            if current_size >= expected_size * 0.9:  # 期待サイズの90%以上なら正常とみなす
                print(f"✅ {model['filename']} は既に正しいサイズでダウンロード済み ({current_size/1024/1024:.2f} MB)")
                continue
            else:
                print(f"🗑️ 小さすぎるファイルを削除: {destination} ({current_size} bytes)")
                destination.unlink()
        
        try:
            actual_size = download_file_with_progress(model["url"], destination)
            
            if actual_size >= model["expected_size"] * 0.9:
                print(f"✅ {model['filename']} のダウンロードが成功しました")
            else:
                print(f"⚠️ 警告: {model['filename']} のサイズが期待値より小さいです")
                
        except Exception as e:
            print(f"❌ {model['filename']} のダウンロードに失敗: {e}")
    
    # 最終確認
    print("\n=== モデルファイル最終確認 ===")
    for file in models_dir.glob("*.onnx"):
        size = file.stat().st_size
        status = "✅" if size > 10 * 1024 * 1024 else "⚠️"  # 10MB以上で正常
        print(f"{status} {file.name}: {size/1024/1024:.2f} MB")

if __name__ == "__main__":
    main() 