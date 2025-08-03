"""
認証設定管理
認証方式の設定保存・読み込みを管理
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from auto_mosaic.src.utils import logger, get_app_data_dir

class AuthMethod(Enum):
    """認証方式の列挙"""
    MONTHLY_PASSWORD = "monthly_password"
    DISCORD = "discord"

class AuthConfig:
    """認証設定管理クラス"""
    
    def __init__(self):
        self.app_data_dir = Path(get_app_data_dir())
        self.config_dir = self.app_data_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "auth_config.json"
        
        # デフォルト設定
        self.default_config = {
            "auth_method": AuthMethod.MONTHLY_PASSWORD.value,
            "allow_method_switching": True,
            "last_successful_method": None,
            "created_at": None,
            "last_modified": None
        }
    
    def is_developer_mode(self) -> bool:
        """
        開発者モード（認証方式切り替え可能）かどうかを判定
        
        判定基準:
        .envファイルのDEVELOPER_MODE設定のみを使用（統一化）
        """
        try:
            # env_configの統一された判定ロジックを使用
            from auto_mosaic.src.env_config import get_env_config
            env_config = get_env_config()
            is_dev = env_config.is_developer_mode()
            
            logger.debug(f"Developer mode: {is_dev} (via .env DEVELOPER_MODE setting)")
            return is_dev
            
        except Exception as e:
            logger.error(f"Error checking developer mode: {e}")
            # フォールバック: 環境変数から直接読み取り
            try:
                from dotenv import load_dotenv
                load_dotenv()
                dev_mode = os.getenv('DEVELOPER_MODE', 'false').strip().lower()
                is_dev = dev_mode in ('true', '1', 'yes', 'on')
                logger.debug(f"Developer mode fallback: {is_dev}")
                return is_dev
            except:
                logger.warning("Developer mode check failed, defaulting to False")
                return False
    
    def is_auth_method_switching_available(self) -> bool:
        """
        認証方式切り替え機能が利用可能かどうかを判定
        
        Returns:
            bool: 切り替え機能が利用可能な場合True
        """
        try:
            # 開発者モードの場合は常に利用可能
            if self.is_developer_mode():
                return True
            
            # ファイルが存在する場合のみ設定をチェック（循環依存を回避）
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 設定で明示的に許可されている場合
                    if config.get('force_allow_switching', False):
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to read config for switching check: {e}")
            
            # 特定ユーザー向けの許可設定
            if self._is_special_user():
                return True
            
            # 一般配布版では利用不可
            return False
            
        except Exception as e:
            logger.error(f"Error checking auth method switching availability: {e}")
            return False
    
    def _is_special_user(self) -> bool:
        """
        特定ユーザー（テストユーザーなど）かどうかを判定
        統一化により開発者モード判定に統合
        """
        # 開発者モードと同一の判定を使用
        return self.is_developer_mode()
    
    def get_default_auth_method_for_distribution(self) -> AuthMethod:
        """
        一般配布版でのデフォルト認証方式を取得
        """
        # 一般配布版ではDiscord認証のみ
        return AuthMethod.DISCORD
    
    def load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        try:
            if not self.config_file.exists():
                logger.info("Auth config file not found, creating default config")
                return self._create_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 設定の妥当性チェック
            config = self._validate_config(config)
            
            logger.debug(f"Auth config loaded: method={config.get('auth_method')}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load auth config: {e}")
            return self._create_default_config()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """設定を保存"""
        try:
            # 設定の妥当性チェック
            config = self._validate_config(config)
            
            # 最終更新日時を設定
            from datetime import datetime
            config['last_modified'] = datetime.now().isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Auth config saved: method={config.get('auth_method')}, dev_mode={config.get('was_developer_mode', False)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save auth config: {e}")
            return False
    
    def get_auth_method(self) -> AuthMethod:
        """現在の認証方式を取得"""
        config = self.load_config()
        
        # 開発者モードの場合は月次認証を優先
        if self.is_developer_mode():
            current_method = config.get('auth_method', AuthMethod.MONTHLY_PASSWORD.value)
            logger.debug(f"Developer mode: configured auth method: {current_method}")
            
            # 開発者モードでは必ず月次認証を使用（ensure_developer_mode_settingsで既に処理済み）
            try:
                return AuthMethod(current_method)
            except ValueError:
                logger.warning(f"Invalid auth method in config: {current_method}, defaulting to monthly password")
                return AuthMethod.MONTHLY_PASSWORD
        
        # 認証方式切り替えが利用できない場合は強制的にDiscord認証
        if not self.is_auth_method_switching_available():
            default_method = self.get_default_auth_method_for_distribution()
            # 設定も更新
            if config.get('auth_method') != default_method.value:
                config['auth_method'] = default_method.value
                self.save_config(config)
            return default_method
        
        method_str = config.get('auth_method', AuthMethod.MONTHLY_PASSWORD.value)
        
        try:
            return AuthMethod(method_str)
        except ValueError:
            logger.warning(f"Invalid auth method in config: {method_str}, using default")
            return AuthMethod.MONTHLY_PASSWORD
    
    def set_auth_method(self, method: AuthMethod) -> bool:
        """認証方式を設定"""
        try:
            # 認証方式切り替えが利用できない場合は拒否
            if not self.is_auth_method_switching_available():
                logger.warning("Auth method switching not available for this user")
                return False
            
            config = self.load_config()
            config['auth_method'] = method.value
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to set auth method: {e}")
            return False
    
    def is_method_switching_allowed(self) -> bool:
        """認証方式の切り替えが許可されているかチェック"""
        return self.is_auth_method_switching_available()
    
    def set_last_successful_method(self, method: AuthMethod) -> bool:
        """最後に成功した認証方式を記録"""
        try:
            config = self.load_config()
            config['last_successful_method'] = method.value
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to set last successful method: {e}")
            return False
    
    def get_last_successful_method(self) -> Optional[AuthMethod]:
        """最後に成功した認証方式を取得"""
        # 認証方式切り替えが利用できない場合は考慮しない
        if not self.is_auth_method_switching_available():
            return None
            
        config = self.load_config()
        method_str = config.get('last_successful_method')
        
        if not method_str:
            return None
        
        try:
            return AuthMethod(method_str)
        except ValueError:
            logger.warning(f"Invalid last successful method in config: {method_str}")
            return None
    
    def _create_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を作成"""
        from datetime import datetime
        
        config = self.default_config.copy()
        
        # 開発者モードの場合は月次認証をデフォルトに
        if self.is_developer_mode():
            config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
            logger.info("Developer mode: defaulting to monthly password authentication")
        # 一般配布版の場合はDiscord認証をデフォルトに（循環依存回避のため直接判定）
        else:
            config['auth_method'] = self.get_default_auth_method_for_distribution().value
        
        config['created_at'] = datetime.now().isoformat()
        config['last_modified'] = datetime.now().isoformat()
        
        # デフォルト設定を直接ファイルに保存（save_configを使わずに循環参照を回避）
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.debug("Default auth config created and saved")
        except Exception as e:
            logger.error(f"Failed to save default auth config: {e}")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """設定の妥当性をチェックして修正"""
        validated_config = self.default_config.copy()
        
        # 既存の設定をマージ
        for key, value in config.items():
            if key in validated_config:
                validated_config[key] = value
        
        # auth_methodの妥当性チェック
        auth_method = validated_config.get('auth_method')
        try:
            AuthMethod(auth_method)
        except (ValueError, TypeError):
            logger.warning(f"Invalid auth_method '{auth_method}', using default")
            # 開発者モードでは月次認証を優先
            if self.is_developer_mode():
                validated_config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
            # 一般配布版ではDiscord認証、開発版では月次認証
            elif self.is_auth_method_switching_available():
                validated_config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
            else:
                validated_config['auth_method'] = self.get_default_auth_method_for_distribution().value
        
        # last_successful_methodの妥当性チェック
        last_method = validated_config.get('last_successful_method')
        if last_method is not None:
            try:
                AuthMethod(last_method)
            except (ValueError, TypeError):
                logger.warning(f"Invalid last_successful_method '{last_method}', clearing")
                validated_config['last_successful_method'] = None
        
        return validated_config
    
    def reset_config(self) -> bool:
        """設定をリセット"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            
            self._create_default_config()
            logger.info("Auth config reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset auth config: {e}")
            return False
    
        # 注意: create_developer_mode_file と create_special_user_file は削除されました
    # 開発者モードは .env の DEVELOPER_MODE 設定のみで制御されます
    
    def switch_to_monthly_auth_for_developer(self) -> bool:
        """
        開発者モード時に月次認証に切り替え
        """
        try:
            if not self.is_developer_mode():
                logger.warning("Not in developer mode - cannot switch to monthly auth")
                return False
            
            config = self.load_config()
            config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
            
            if self.save_config(config):
                logger.info("Developer mode: switched to monthly password authentication")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch to monthly auth: {e}")
            return False
    
    def ensure_developer_mode_settings(self) -> None:
        """
        開発者モード時の設定を確実に適用、または通常モード時に復元
        """
        try:
            config = self.load_config()
            current_method = config.get('auth_method')
            dev_mode_active = self.is_developer_mode()
            
            # 開発者モードの状態を追跡するフラグを確認
            was_dev_mode = config.get('was_developer_mode', False)
            
            if dev_mode_active:
                # 開発者モード中の処理
                if current_method == AuthMethod.DISCORD.value:
                    logger.info("Developer mode: switching from Discord to monthly password authentication")
                    config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
                    config['previous_auth_method'] = AuthMethod.DISCORD.value  # 元の設定を保存
                    config['was_developer_mode'] = True
                    self.save_config(config)
                elif current_method != AuthMethod.MONTHLY_PASSWORD.value:
                    logger.info(f"Developer mode: setting auth method to monthly password (was: {current_method})")
                    config['auth_method'] = AuthMethod.MONTHLY_PASSWORD.value
                    config['previous_auth_method'] = current_method  # 元の設定を保存
                    config['was_developer_mode'] = True
                    self.save_config(config)
                else:
                    # 既に月次認証の場合も、開発者モードフラグを設定
                    if not was_dev_mode:
                        config['was_developer_mode'] = True
                        config['previous_auth_method'] = config.get('previous_auth_method', AuthMethod.DISCORD.value)
                        self.save_config(config)
                    logger.debug("Developer mode: auth method already set to monthly password")
                    
            else:
                # 通常モード（開発者モードでない場合）
                if was_dev_mode:
                    # 開発者モードから通常モードに戻った場合、元の設定を復元
                    previous_method = config.get('previous_auth_method', AuthMethod.DISCORD.value)
                    logger.info(f"Exiting developer mode: restoring auth method to {previous_method}")
                    
                    config['auth_method'] = previous_method
                    config['was_developer_mode'] = False
                    config.pop('previous_auth_method', None)  # 一時保存データを削除
                    self.save_config(config)
                    
        except Exception as e:
            logger.error(f"Failed to ensure developer mode settings: {e}")
    
    def get_developer_mode_status(self) -> dict:
        """
        開発者モードの状態情報を取得（デバッグ用）
        """
        try:
            config = self.load_config()
            return {
                'is_developer_mode': self.is_developer_mode(),
                'current_auth_method': config.get('auth_method'),
                'was_developer_mode': config.get('was_developer_mode', False),
                'previous_auth_method': config.get('previous_auth_method'),
                'environment_variable': os.getenv('AUTO_MOSAIC_DEV_MODE')
            }
        except Exception as e:
            logger.error(f"Failed to get developer mode status: {e}")
            return {} 