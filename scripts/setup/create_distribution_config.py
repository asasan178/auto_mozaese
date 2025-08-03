#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配布用暗号化設定ファイル作成スクリプト
開発者が.envファイルから暗号化された認証設定を生成するためのツール
"""

import sys
from pathlib import Path

# auto_mosaicモジュールをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent / "auto_mosaic"))

def check_auth_files():
    """認証ファイルの存在確認（ビルド時用）"""
    from auto_mosaic.src.utils import get_app_data_dir
    
    app_data_dir = Path(get_app_data_dir())
    auth_file = app_data_dir / 'config' / 'auth.dat'
    salt_file = app_data_dir / 'config' / 'auth.salt'
    
    if auth_file.exists() and salt_file.exists():
        print('    [OK] Distribution auth files ready at %AppData%')
        print(f'    📂 Auth location: {app_data_dir / "config"}')
        print('    💡 Files will be auto-detected by users AppData folder')
        return True
    else:
        print('    [WARN] Distribution auth files not found')
        print('    💡 Run create_distribution_config.py to generate auth files')
        print(f'    📂 Expected location: {app_data_dir / "config"}')
        return False

def check_model_files():
    """モデルファイルの存在確認（ビルド時用）"""
    try:
        from auto_mosaic.src.downloader import downloader
        missing = downloader.get_missing_models_info()
        all_models = ['anime_nsfw_v4']
        missing_models = [m for m in all_models if m in missing]
        
        if missing_models:
            print(f'    ⚠️  Missing models: {missing_models}')
            print('    📥 For developers: Manual download recommended')
        else:
            print('    ✅ All model files ready')
        print(f'    📊 Available models: {len(all_models) - len(missing_models)}/{len(all_models)}')
        return len(missing_models) == 0
    except Exception as e:
        print(f'    [ERROR] Model check failed: {e}')
        return False

def main():
    """配布用設定ファイル作成のメイン処理"""
    import sys
    
    # オプションの処理
    if len(sys.argv) > 1:
        if sys.argv[1] == '--check':
            return check_auth_files()
        elif sys.argv[1] == '--check-models':
            return check_model_files()
    
    from auto_mosaic.src.encrypted_config import create_distribution_package
    from auto_mosaic.src.utils import get_app_data_dir
    
    print("=" * 60)
    print("🔐 配布用暗号化設定ファイル作成ツール")
    print("=" * 60)
    
    # 出力先の説明
    app_data_dir = get_app_data_dir()
    print(f"📂 設定ファイル出力先: {app_data_dir / 'config'}")
    print("💡 配布版では %AppData%\\自動モザエセ\\config に配置されます")
    print()
    
    # 現在の.env設定確認
    print("📋 現在の.env設定を確認中...")
    
    try:
        success = create_distribution_package()
        
        if success:
            print()
            print("✅ 配布用設定ファイルの作成が完了しました！")
            print()
            print("📦 配布版への組み込み手順:")
            print("1. 以下のファイルをコピー:")
            print(f"   - {app_data_dir / 'config' / 'auth.dat'}")
            print(f"   - {app_data_dir / 'config' / 'auth.salt'}")
            print()
            print("2. 配布版実行時の配置:")
            print("   - ユーザーの %AppData%\\自動モザエセ\\config\\ フォルダに自動配置")
            print("   - 他の設定ファイル（ログ、モデル等）と同じ場所で統一管理")
            print()
            print("🔒 セキュリティ:")
            print("   - 設定は AES暗号化 + PBKDF2キー導出で保護されています")
            print("   - マスターキー: AUTO_MOSAIC_DIST_2025")
            
        else:
            print("❌ 配布用設定ファイルの作成に失敗しました")
            print("📝 .envファイルの設定を確認してください")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        print("\n詳細なエラー情報:")
        traceback.print_exc()

if __name__ == "__main__":
    main() 