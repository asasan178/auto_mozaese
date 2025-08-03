#!/usr/bin/env python3
"""
Discord設定読み込みテスト - 配布版での動作確認
"""

import sys
from pathlib import Path

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

def test_discord_config():
    print("🔍 Discord設定読み込みテスト開始")
    print("=" * 60)
    
    try:
        # 1. cryptographyのインポートテスト
        print("1️⃣ cryptographyライブラリテスト")
        try:
            import cryptography
            print(f"   ✅ cryptography version: {cryptography.__version__}")
            
            from cryptography.fernet import Fernet
            print("   ✅ Fernet import successful")
            
            # 簡単な暗号化テスト
            key = Fernet.generate_key()
            f = Fernet(key)
            token = f.encrypt(b"test message")
            decrypted = f.decrypt(token)
            print(f"   ✅ 暗号化テスト成功: {decrypted.decode()}")
            
        except Exception as e:
            print(f"   ❌ cryptographyエラー: {e}")
            return False
        
        # 2. 設定ファイル確認
        print("\n2️⃣ 設定ファイル確認")
        from auto_mosaic.src.encrypted_config import EncryptedConfigManager
        
        manager = EncryptedConfigManager()
        print(f"   設定ファイル: {manager.encrypted_config_file}")
        print(f"   存在: {manager.encrypted_config_file.exists()}")
        print(f"   ソルトファイル: {manager.salt_file}")
        print(f"   存在: {manager.salt_file.exists()}")
        
        # 3. 復号化テスト
        print("\n3️⃣ 復号化テスト")
        if manager.is_encrypted_config_available():
            print("   ✅ 暗号化設定利用可能")
            try:
                config = manager.decrypt_config()
                if config:
                    print("   ✅ 復号化成功!")
                    print(f"   Client ID: {config.get('client_id')}")
                    print(f"   ギルド数: {len(config.get('guilds', []))}")
                else:
                    print("   ❌ 復号化失敗 - Noneが返された")
            except Exception as e:
                print(f"   ❌ 復号化エラー: {e}")
                import traceback
                print(f"   詳細: {traceback.format_exc()}")
        else:
            print("   ❌ 暗号化設定利用不可")
        
        # 4. DistributionConfigLoaderテスト
        print("\n4️⃣ DistributionConfigLoaderテスト")
        from auto_mosaic.src.encrypted_config import DistributionConfigLoader
        
        loader = DistributionConfigLoader()
        discord_config = loader.load_discord_config()
        
        print(f"   最終的なClient ID: {discord_config.get('client_id')}")
        print(f"   最終的なギルド数: {len(discord_config.get('guilds', []))}")
        
        if discord_config.get('client_id') == 'demo_client_id':
            print("   ⚠️  フォールバック設定が使用されています!")
            return False
        else:
            print("   ✅ 正常な設定が読み込まれました")
            return True
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_discord_config()
    print("\n" + "=" * 60)
    if success:
        print("✅ Discord設定テスト成功")
    else:
        print("❌ Discord設定テスト失敗")
    input("Enterキーを押して終了...") 