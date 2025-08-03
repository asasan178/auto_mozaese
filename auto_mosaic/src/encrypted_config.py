"""
暗号化された設定ファイル管理モジュール
一般配布時に認証情報を安全に埋め込むためのシステム
"""
import os
import base64
import json
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sys

class EncryptedConfigManager:
    """暗号化された設定ファイルの管理"""
    
    def __init__(self):
        # %AppData%の自動モザエセフォルダに統一（他の設定ファイルと同じ場所）
        from auto_mosaic.src.utils import get_app_data_dir
        
        if getattr(sys, 'frozen', False):
            # PyInstaller環境（exe実行時）- AppDataフォルダを使用
            self.app_data_dir = Path(get_app_data_dir())
            print(f"🔧 PyInstaller環境検出 - AppData使用: {self.app_data_dir}")
        else:
            # 通常のPython環境 - プロジェクトルートを使用
            self.app_data_dir = Path(get_app_data_dir())
            print(f"🐍 通常のPython環境 - プロジェクトルート使用: {self.app_data_dir}")
            
        self.encrypted_config_file = self.app_data_dir / "config" / "auth.dat"
        self.salt_file = self.app_data_dir / "config" / "auth.salt"
        
        print(f"📂 設定ファイルパス: {self.encrypted_config_file}")
        print(f"🔑 ソルトファイルパス: {self.salt_file}")
        
        # 配布用のマスターキー（実際には別の方法で隠匿）
        self.master_key = "AUTO_MOSAIC_DIST_2025"
        
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """パスワードから暗号化キーを導出"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _get_or_create_salt(self) -> bytes:
        """ソルトを取得または生成"""
        if self.salt_file.exists():
            return self.salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            self.salt_file.parent.mkdir(parents=True, exist_ok=True)
            self.salt_file.write_bytes(salt)
            return salt
    
    def encrypt_config(self, config_data: Dict[str, Any], password: str = None) -> bool:
        """設定データを暗号化して保存"""
        try:
            # パスワードが指定されていない場合はマスターキーを使用
            if password is None:
                password = self.master_key
            
            # ソルトを取得
            salt = self._get_or_create_salt()
            
            # 暗号化キーを導出
            key = self._derive_key(password, salt)
            fernet = Fernet(key)
            
            # 設定データをJSON形式でシリアライズ
            json_data = json.dumps(config_data, ensure_ascii=False, indent=2)
            
            # 暗号化
            encrypted_data = fernet.encrypt(json_data.encode('utf-8'))
            
            # 暗号化されたファイルを保存
            self.encrypted_config_file.parent.mkdir(parents=True, exist_ok=True)
            self.encrypted_config_file.write_bytes(encrypted_data)
            
            print(f"✅ 設定が暗号化されて保存されました: {self.encrypted_config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 設定の暗号化に失敗: {e}")
            return False
    
    def decrypt_config(self, password: str = None) -> Optional[Dict[str, Any]]:
        """暗号化された設定データを復号化"""
        try:
            # パスワードが指定されていない場合はマスターキーを使用
            if password is None:
                password = self.master_key
            
            # 暗号化ファイルが存在しない場合
            if not self.encrypted_config_file.exists():
                return None
            
            # ソルトを取得
            if not self.salt_file.exists():
                return None
            salt = self.salt_file.read_bytes()
            
            # 暗号化キーを導出
            key = self._derive_key(password, salt)
            fernet = Fernet(key)
            
            # 暗号化されたデータを読み込み
            encrypted_data = self.encrypted_config_file.read_bytes()
            
            # 復号化
            decrypted_data = fernet.decrypt(encrypted_data)
            json_data = decrypted_data.decode('utf-8')
            
            # JSONデータをパース
            config_data = json.loads(json_data)
            
            return config_data
            
        except Exception as e:
            print(f"❌ 設定の復号化に失敗: {e}")
            return None
    
    def is_encrypted_config_available(self) -> bool:
        """暗号化された設定ファイルが利用可能かチェック"""
        return (self.encrypted_config_file.exists() and 
                self.salt_file.exists())
    
    def create_distribution_config(self, discord_config: Dict[str, Any]) -> bool:
        """配布用の暗号化設定ファイルを作成"""
        """
        discord_config の例:
        {
            "client_id": "1352190948905582642",
            "client_secret": "s6fGNhtF6yDjYUTlvCn4SE2A93hNJWTL",
            "guilds": [
                {
                    "guild_id": "1267610168217305211",
                    "name": "マスターコンサル",
                    "required_roles": ["1368195168368459786"]
                },
                {
                    "guild_id": "1350693921101185096", 
                    "name": "AI開発講座",
                    "required_roles": ["1351953855839207479", "1352793968794013696"]
                }
            ],
            "redirect_uri": "http://localhost:8000/callback",
            "scopes": ["identify", "guilds", "guilds.members.read"],
            "max_failures": 3,
            "cooldown": 10
        }
        """
        return self.encrypt_config(discord_config)


class DistributionConfigLoader:
    """配布版での設定読み込み"""
    
    def __init__(self):
        self.encrypted_manager = EncryptedConfigManager()
        self.fallback_config = self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """フォールバック設定（開発者モード用）"""
        return {
            "client_id": "demo_client_id",
            "client_secret": "demo_client_secret", 
            "guilds": [
                {
                    "guild_id": "demo_guild_1",
                    "name": "デモサーバー1",
                    "required_roles": ["demo_role_1"]
                }
            ],
            "redirect_uri": "http://localhost:8000/callback",
            "scopes": ["identify", "guilds", "guilds.members.read"],
            "max_failures": 1,
            "cooldown": 10
        }
    
    def load_discord_config(self) -> Dict[str, Any]:
        """Discord設定を読み込み（優先順位付き）"""
        print("=" * 50)
        print("🔍 Discord設定読み込み開始")
        print("=" * 50)
        
        try:
            # 1. 暗号化された設定ファイルから読み込み（配布版）
            print(f"📂 暗号化設定ファイル確認...")
            print(f"   設定ファイル: {self.encrypted_manager.encrypted_config_file}")
            print(f"   存在: {self.encrypted_manager.encrypted_config_file.exists()}")
            print(f"   ソルトファイル: {self.encrypted_manager.salt_file}")
            print(f"   存在: {self.encrypted_manager.salt_file.exists()}")
            
            if self.encrypted_manager.is_encrypted_config_available():
                print("✅ 暗号化設定ファイルが利用可能")
                try:
                    print("🔐 復号化を試行中...")
                    encrypted_config = self.encrypted_manager.decrypt_config()
                    if encrypted_config:
                        print("✅ 復号化成功!")
                        print(f"   Client ID: {encrypted_config.get('client_id', 'NOT_FOUND')}")
                        print(f"   ギルド数: {len(encrypted_config.get('guilds', []))}")
                        
                        # 開発者モードでのみメッセージを表示
                        from auto_mosaic.src.env_config import get_env_config
                        try:
                            env_config = get_env_config()
                            if env_config.is_developer_mode():
                                print("🔐 暗号化された設定ファイルから読み込み")
                        except Exception:
                            pass  # エラーが発生した場合は非表示
                        
                        # max_failuresを強制的に1に設定（認証失敗時間の短縮）
                        encrypted_config['max_failures'] = 1
                        
                        return encrypted_config
                    else:
                        print("❌ 復号化失敗 - Noneが返されました")
                except Exception as decrypt_error:
                    print(f"❌ 暗号化設定の復号化エラー: {decrypt_error}")
                    print("   cryptographyライブラリの問題またはファイル破損の可能性があります")
                    import traceback
                    print(f"   詳細エラー: {traceback.format_exc()}")
            else:
                print("❌ 暗号化設定ファイルが利用不可")
            
            # 2. .envファイルから読み込み（開発者モード）
            print("📋 .envファイル確認中...")
            from auto_mosaic.src.env_config import get_env_config
            env_config = get_env_config()
            
            if env_config.is_developer_mode():
                print("🔧 開発者モード: .envファイルから読み込み")
                return self._load_from_env_config(env_config)
            
            # 3. フォールバック設定（デモモード）
            print("📋 フォールバック設定を使用")
            print("⚠️  配布版では正常なDiscord認証情報が必要です")
            return self.fallback_config
            
        except Exception as e:
            print(f"❌ 設定読み込みエラー: {e}")
            import traceback
            print(f"   詳細: {traceback.format_exc()}")
            return self.fallback_config
    
    def _load_from_env_config(self, env_config) -> Dict[str, Any]:
        """環境設定から Discord 設定を構築"""
        guild_configs = env_config.get_discord_guild_configs()
        
        return {
            "client_id": env_config.get_discord_client_id() or "demo_client_id",
            "client_secret": env_config.get_discord_client_secret() or "demo_client_secret",
            "guilds": [
                {
                    "guild_id": guild["guild_id"],
                    "name": guild["name"],
                    "required_roles": guild["required_roles"]
                }
                for guild in guild_configs
            ],
            "redirect_uri": env_config.get_discord_redirect_uri(),
            "scopes": env_config.get_discord_scopes(),
            "max_failures": env_config.get_discord_max_consecutive_failures(),
            "cooldown": env_config.get_discord_role_check_cooldown()
        }


def create_distribution_package():
    """配布用のパッケージ作成（開発者用ツール）"""
    from auto_mosaic.src.env_config import get_env_config
    
    print("📦 配布用暗号化設定パッケージを作成します...")
    
    # 現在の.env設定を読み込み
    env_config = get_env_config()
    
    if not env_config.is_developer_mode():
        print("❌ 開発者モードが有効になっていません")
        return False
    
    # Discord設定を取得
    guild_configs = env_config.get_discord_guild_configs()
    
    discord_config = {
        "client_id": env_config.get_discord_client_id(),
        "client_secret": env_config.get_discord_client_secret(),
        "guilds": [
            {
                "guild_id": guild["guild_id"],
                "name": guild["name"], 
                "required_roles": guild["required_roles"]
            }
            for guild in guild_configs
        ],
        "redirect_uri": env_config.get_discord_redirect_uri(),
        "scopes": env_config.get_discord_scopes(),
        "max_failures": env_config.get_discord_max_consecutive_failures(),
        "cooldown": env_config.get_discord_role_check_cooldown()
    }
    
    # 暗号化して保存
    manager = EncryptedConfigManager()
    success = manager.create_distribution_config(discord_config)
    
    if success:
        print("✅ 配布用設定パッケージが作成されました")
        print(f"📂 暗号化ファイル: {manager.encrypted_config_file}")
        print(f"🔑 ソルトファイル: {manager.salt_file}")
        print("\n💡 これらのファイルを配布版に含めてください")
        return True
    else:
        print("❌ 配布用設定パッケージの作成に失敗しました")
        return False


if __name__ == "__main__":
    # 配布用パッケージ作成のテスト
    create_distribution_package() 