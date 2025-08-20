"""
環境変数設定管理モジュール
.envファイルからの設定読み込みとフォールバック機能を提供
"""
import os
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class EnvironmentConfig:
    """環境変数設定管理クラス"""
    
    def __init__(self):
        self._env_loaded = False
        self._load_environment()
    
    def _load_environment(self):
        """環境変数を読み込み"""
        if DOTENV_AVAILABLE and not self._env_loaded:
            # .envファイルを探索して読み込み
            env_paths = [
                Path(".env"),  # カレントディレクトリ
                Path.cwd() / ".env",  # 実行ディレクトリ
                Path(__file__).parent.parent.parent / ".env",  # プロジェクトルート
            ]
            
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    self._env_loaded = True
                    break
    
    def _is_developer_mode_active(self) -> bool:
        """開発者モードが有効かどうかを確認（統一化により単純化）"""
        try:
            # .envのDEVELOPER_MODE設定のみを使用
            return self.is_developer_mode()
        except Exception:
            return False
    
    def get_master_password_hash(self) -> str:
        """マスターパスワードハッシュを取得（開発者モードでのみ実際の値を返す）"""
        # 開発者モード以外では常にデモ用パスワード
        if not self._is_developer_mode_active():
            return hashlib.sha256("demo".encode()).hexdigest()
        
        # 開発者モードでのみ環境変数から取得を試行
        env_hash = os.getenv('MASTER_PASSWORD_HASH', '').strip()
        if env_hash and env_hash != 'demo_password_hash_here':
            return env_hash
        
        # フォールバック: デモ用パスワード（"demo"のハッシュ）
        return hashlib.sha256("demo".encode()).hexdigest()
    
    def get_monthly_passwords(self) -> Dict[str, str]:
        """月次パスワードハッシュ辞書を取得（開発者モードでのみ実際の値を返す）"""
        monthly_passwords = {}
        
        # 開発者モード以外では常にデモ用パスワード
        is_dev_mode = self._is_developer_mode_active()
        
        # 2025年の各月をチェック
        for month in range(1, 13):
            month_key = f"2025-{month:02d}"
            env_key = f"MONTHLY_PASSWORD_2025_{month:02d}"
            
            if is_dev_mode:
                # 開発者モードでのみ環境変数から取得を試行
                env_hash = os.getenv(env_key, '').strip()
                if env_hash and not env_hash.startswith('demo_hash_'):
                    monthly_passwords[month_key] = env_hash
                    continue
            
            # フォールバック: デモ用パスワード（"demo_YYYY_MM"のハッシュ）
            demo_password = f"demo_{month_key.replace('-', '_')}"
            monthly_passwords[month_key] = hashlib.sha256(demo_password.encode()).hexdigest()
        
        return monthly_passwords
    
    def get_civitai_api_key(self) -> Optional[str]:
        """CivitAI APIキーを取得"""
        api_key = os.getenv('CIVITAI_API_KEY', '').strip()
        return api_key if api_key else None
    
    def get_discord_client_id(self) -> Optional[str]:
        """Discord Client IDを取得"""
        client_id = os.getenv('DISCORD_CLIENT_ID', '').strip()
        return client_id if client_id else None
    
    def get_discord_client_secret(self) -> Optional[str]:
        """Discord Client Secretを取得"""
        client_secret = os.getenv('DISCORD_CLIENT_SECRET', '').strip()
        return client_secret if client_secret else None
    
    def get_discord_redirect_uri(self) -> str:
        """Discord Redirect URIを取得"""
        return os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:8000/callback').strip()
    
    def get_discord_scopes(self) -> list:
        """Discord スコープリストを取得"""
        scopes_str = os.getenv('DISCORD_SCOPES', 'identify,guilds,guilds.members.read').strip()
        return [scope.strip() for scope in scopes_str.split(',') if scope.strip()]
    
    def get_discord_max_consecutive_failures(self) -> int:
        """Discord最大連続失敗回数を取得"""
        try:
            return int(os.getenv('DISCORD_MAX_CONSECUTIVE_FAILURES', '1'))
        except ValueError:
            return 1
    
    def get_discord_role_check_cooldown(self) -> int:
        """Discordロールチェックのクールダウン時間を取得"""
        try:
            return int(os.getenv('DISCORD_ROLE_CHECK_COOLDOWN', '10'))
        except ValueError:
            return 10
    
    def get_discord_guild_configs(self) -> list:
        """Discordギルド設定リストを取得"""
        guild_configs = []
        
        # 最大10個のギルド設定をチェック
        for i in range(1, 11):
            guild_id = os.getenv(f'DISCORD_GUILD_{i}_ID', '').strip()
            if not guild_id:
                continue
                
            guild_name = os.getenv(f'DISCORD_GUILD_{i}_NAME', f'Guild {i}').strip()
            roles_str = os.getenv(f'DISCORD_GUILD_{i}_ROLES', '').strip()
            
            if roles_str:
                required_roles = [role.strip() for role in roles_str.split(',') if role.strip()]
                guild_configs.append({
                    "guild_id": guild_id,
                    "required_roles": required_roles,
                    "name": guild_name
                })
        
        # フォールバック: 環境変数が設定されていない場合はデフォルト設定を返す
        if not guild_configs:
            guild_configs = [
                {
                    "guild_id": "demo_guild_1",
                    "required_roles": ["demo_role_1"],
                    "name": "デモサーバー1"
                }
            ]
        
        return guild_configs
    
    def is_debug_mode(self) -> bool:
        """デバッグモードの状態を取得"""
        debug = os.getenv('DEBUG_MODE', 'false').strip().lower()
        return debug in ('true', '1', 'yes', 'on')
    
    def get_discord_config(self) -> Dict[str, Any]:
        """Discord設定を統合して取得"""
        guild_configs = self.get_discord_guild_configs()
        
        return {
            "client_id": self.get_discord_client_id() or "demo_client_id",
            "client_secret": self.get_discord_client_secret() or "demo_client_secret",
            "guilds": [
                {
                    "guild_id": guild["guild_id"],
                    "name": guild["name"],
                    "required_roles": guild["required_roles"]
                }
                for guild in guild_configs
            ],
            "redirect_uri": self.get_discord_redirect_uri(),
            "scopes": self.get_discord_scopes(),
            "max_failures": self.get_discord_max_consecutive_failures(),
            "cooldown": self.get_discord_role_check_cooldown()
        }

    def is_developer_mode(self) -> bool:
        """開発者モードの状態を取得"""
        # 1. .developer_modeファイルによる判定
        if os.path.exists('.developer_mode'):
            return True
            
        # 2. 環境変数による判定（AUTO_MOSAIC_DEV_MODEを優先）
        dev_mode = os.getenv('AUTO_MOSAIC_DEV_MODE', os.getenv('DEVELOPER_MODE', 'false')).strip().lower()
        return dev_mode in ('true', '1', 'yes', 'on')
    
    def get_log_level(self) -> str:
        """ログレベルを取得"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').strip().upper()
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        return log_level if log_level in valid_levels else 'INFO'
    
    def generate_demo_hash(self, password: str) -> str:
        """デモ用パスワードのハッシュを生成"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validate_env_file(self) -> Dict[str, str]:
        """環境設定の検証結果を返す"""
        validation_results = {}
        is_dev_mode = self._is_developer_mode_active()
        
        # .envファイルの存在確認
        if not DOTENV_AVAILABLE:
            validation_results['dotenv_package'] = 'python-dotenvパッケージがインストールされていません'
        
        # 開発者モード状態の確認
        if not is_dev_mode:
            validation_results['developer_mode'] = '通常モードのため月次パスワード認証は使用されません'
            return validation_results
        
        # 開発者モードでの詳細検証
        validation_results['developer_mode'] = '開発者モード有効 - 月次パスワード認証を使用'
        
        # マスターパスワードの確認
        master_hash = os.getenv('MASTER_PASSWORD_HASH', '').strip()
        if not master_hash or master_hash == 'demo_password_hash_here':
            validation_results['master_password'] = 'マスターパスワードが設定されていません（デモ用パスワードを使用）'
        
        # 月次パスワードの確認
        demo_count = 0
        for month in range(1, 13):
            env_key = f"MONTHLY_PASSWORD_2025_{month:02d}"
            env_hash = os.getenv(env_key, '').strip()
            if not env_hash or env_hash.startswith('demo_hash_'):
                demo_count += 1
        
        if demo_count > 0:
            validation_results['monthly_passwords'] = f'{demo_count}個の月次パスワードがデモ用です'
        else:
            validation_results['monthly_passwords'] = '全ての月次パスワードが設定済みです'
        
        return validation_results


# グローバルインスタンス
_env_config = None

def get_env_config() -> EnvironmentConfig:
    """環境設定のシングルトンインスタンスを取得"""
    global _env_config
    if _env_config is None:
        _env_config = EnvironmentConfig()
    return _env_config 