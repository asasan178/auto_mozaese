"""
Discord認証アダプター
既存のDiscord認証システムをauto_mosaicプロジェクトに統合するためのアダプター
"""

import json
import webbrowser
import requests
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
import threading
import time

# auto_mosaicのユーティリティを使用
from auto_mosaic.src.utils import logger, get_app_data_dir

class DiscordTokenManager:
    """Discord認証トークンの管理"""
    
    def __init__(self):
        self.app_data_dir = Path(get_app_data_dir())
        self.auth_dir = self.app_data_dir / "config" / "discord_auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.auth_dir / "discord_token.json"
        self.token_expiry_hours = 168  # 7日間有効（24 × 7 = 168時間）
        
    def save_token(self, token_data: Dict[str, Any]) -> None:
        """トークンを保存（認証成功時刻は含めない - 認証完了後に別途設定）"""
        try:
            # 有効期限を設定
            expiry_date = datetime.now() + timedelta(hours=self.token_expiry_hours)
            token_data['expiry'] = expiry_date.isoformat()
            
            # last_auth_successは自動設定しない（認証完了後に明示的に設定）
            # 既存のlast_auth_successがある場合は保持する
            try:
                if self.token_file.exists():
                    with open(self.token_file, 'r', encoding='utf-8') as f:
                        existing_token = json.load(f)
                    if existing_token and 'last_auth_success' in existing_token:
                        token_data['last_auth_success'] = existing_token['last_auth_success']
            except Exception as e:
                logger.debug(f"Could not preserve existing last_auth_success: {e}")
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Discord token saved with 7-day expiry: {expiry_date}")
            
        except Exception as e:
            logger.error(f"Failed to save Discord token: {e}")
            raise
    
    def load_token(self) -> Optional[Dict[str, Any]]:
        """トークンを読み込み"""
        try:
            if not self.token_file.exists():
                logger.debug("Discord token file not found")
                return None
            
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 有効期限チェック
            if 'expiry' in token_data:
                expiry = datetime.fromisoformat(token_data['expiry'])
                if datetime.now() > expiry:
                    logger.info("Discord token expired")
                    self.clear_token()
                    return None
            
            logger.debug("Discord token loaded successfully")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to load Discord token: {e}")
            return None
    
    def clear_token(self) -> None:
        """トークンを削除"""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Discord token cleared")
        except Exception as e:
            logger.error(f"Failed to clear Discord token: {e}")

    def save_auth_success(self) -> None:
        """認証成功時刻を保存（認証が完全に完了した時のみ呼び出す）"""
        try:
            token_data = self.load_token()
            if token_data:
                token_data['last_auth_success'] = datetime.now().isoformat()
                with open(self.token_file, 'w', encoding='utf-8') as f:
                    json.dump(token_data, f, ensure_ascii=False, indent=2)
                logger.info("Discord auth: authentication success time saved")
            else:
                logger.warning("Discord auth: cannot save success time - no token data")
        except Exception as e:
            logger.error(f"Failed to save auth success time: {e}")

class DiscordCallbackServer:
    """Discord認証のコールバック受信サーバー"""
    
    def __init__(self, port: int = 8000):
        self.preferred_port = port
        self.port = None  # 実際に使用されるポート
        self.auth_code = None
        self.server_thread = None
        self.stop_event = threading.Event()
        
    def find_available_port(self, start_port: int = 8000, max_attempts: int = 10) -> int:
        """利用可能なポートを見つける（Discord認証で一般的に使用されるポート範囲を優先）"""
        import socket
        import os
        
        # テスト用: 環境変数で強制的にポートを指定
        force_port = os.getenv('DISCORD_AUTH_FORCE_PORT')
        if force_port:
            try:
                force_port_int = int(force_port)
                logger.info(f"🧪 テストモード: ポート{force_port_int}を強制使用")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    # SO_REUSEADDRは使用しない（正確なポート可用性チェックのため）
                    s.bind(('localhost', force_port_int))
                    logger.info(f"✅ 強制指定ポート {force_port_int} を使用")
                    return force_port_int
            except (ValueError, OSError) as e:
                logger.warning(f"❌ 強制指定ポート {force_port} の使用に失敗: {e}")
                logger.info("通常のポート検索に戻ります")
        
        # Discord認証でよく使用されるポート（Discord Developer Portalで設定推奨）
        preferred_ports = [8000, 8080, 3000, 3001, 5000, 5001, 8001, 8081]
        
        # まず推奨ポートを試す（順序通りに検索）
        logger.debug(f"Testing preferred ports in order: {preferred_ports}")
        for port in preferred_ports:
            logger.debug(f"Testing port {port}...")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    # SO_REUSEADDRは使用しない（正確なポート可用性チェックのため）
                    s.bind(('localhost', port))
                    logger.info(f"Found available port (preferred): {port}")
                    return port
            except OSError as e:
                logger.debug(f"Preferred port {port} is already in use: {e}")
                continue
        
        # 推奨ポートが利用できない場合は順次試す
        for port in range(start_port, start_port + max_attempts):
            if port not in preferred_ports:  # 推奨ポートは既にチェック済み
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        # SO_REUSEADDRは使用しない（正確なポート可用性チェックのため）
                        s.bind(('localhost', port))
                        logger.info(f"Found available port: {port}")
                        return port
                except OSError:
                    logger.debug(f"Port {port} is already in use")
                    continue
        
        logger.warning(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")
        raise OSError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")
        
    def get_actual_port(self) -> int:
        """実際に使用されているポートを取得"""
        return self.port
        
    def start(self) -> None:
        """サーバーを開始"""
        try:
            # 利用可能なポートを見つける
            self.port = self.find_available_port(self.preferred_port)
            
            import http.server
            import socketserver
            from urllib.parse import urlparse, parse_qs
            
            class CallbackHandler(http.server.BaseHTTPRequestHandler):
                def __init__(self, server_instance, *args, **kwargs):
                    self.server_instance = server_instance
                    super().__init__(*args, **kwargs)
                
                def do_GET(self):
                    try:
                        parsed_url = urlparse(self.path)
                        if parsed_url.path == '/callback':
                            query_params = parse_qs(parsed_url.query)
                            if 'code' in query_params:
                                self.server_instance.auth_code = query_params['code'][0]
                                
                                # 成功レスポンス
                                self.send_response(200)
                                self.send_header('Content-type', 'text/html; charset=utf-8')
                                self.end_headers()
                                
                                success_html = """
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <meta charset="UTF-8">
                                    <title>認証コード取得完了</title>
                                    <style>
                                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                        .success { color: #4CAF50; font-size: 24px; margin-bottom: 20px; }
                                        .info { color: #666; font-size: 16px; margin-bottom: 10px; }
                                        .processing { color: #ff9800; font-size: 14px; }
                                    </style>
                                </head>
                                <body>
                                    <div class="success">✅ Discord認証コードを取得しました</div>
                                    <div class="info">このタブを閉じて、アプリケーションに戻ってください。</div>
                                    <div class="processing">※ アプリでロール確認を行っています...</div>
                                    <script>
                                        setTimeout(function() { window.close(); }, 3000);
                                    </script>
                                </body>
                                </html>
                                """.encode('utf-8')
                                
                                self.wfile.write(success_html)
                                return
                            else:
                                # エラーレスポンス
                                self.send_response(400)
                                self.send_header('Content-type', 'text/html; charset=utf-8')
                                self.end_headers()
                                
                                error_html = """
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <meta charset="UTF-8">
                                    <title>認証エラー</title>
                                    <style>
                                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                                        .error { color: #f44336; font-size: 24px; margin-bottom: 20px; }
                                        .info { color: #666; font-size: 16px; }
                                    </style>
                                </head>
                                <body>
                                    <div class="error">❌ 認証に失敗しました</div>
                                    <div class="info">認証コードが見つかりません。アプリケーションから再度お試しください。</div>
                                </body>
                                </html>
                                """.encode('utf-8')
                                
                                self.wfile.write(error_html)
                        else:
                            self.send_response(404)
                            self.end_headers()
                            
                    except Exception as e:
                        logger.error(f"Callback handler error: {e}")
                        self.send_response(500)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    # ログ出力を抑制
                    pass
            
            def create_handler(*args, **kwargs):
                return CallbackHandler(self, *args, **kwargs)
            
            with socketserver.TCPServer(("", self.port), create_handler) as httpd:
                logger.info(f"Discord callback server started on port {self.port}")
                
                while not self.stop_event.is_set():
                    httpd.handle_request()
                    if self.auth_code:
                        break
                        
        except Exception as e:
            logger.error(f"Failed to start Discord callback server: {e}")
    
    def stop(self) -> None:
        """サーバーを停止"""
        self.stop_event.set()
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1)
    
    def wait_for_code(self, timeout: int = 300) -> Optional[str]:
        """認証コードを待機"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.auth_code:
                return self.auth_code
            time.sleep(0.1)
        return None

class DiscordAuthAdapter:
    """Discord認証システムのアダプター（複数サーバー対応）"""
    
    # クラス変数でキャッシュを共有（インスタンス間で共有）
    _shared_last_successful_auth_time = 0
    _shared_consecutive_failures = 0
    _shared_last_role_check_time = 0
    
    def __init__(self):
        # 暗号化された設定またはenv設定を読み込み
        try:
            # 配布版では暗号化設定を使用
            from auto_mosaic.src.encrypted_config import DistributionConfigLoader
            config_loader = DistributionConfigLoader()
            self.config = config_loader.load_discord_config()
            logger.info("Discord auth: using encrypted configuration")
        except ImportError:
            # 開発版ではenv設定を使用
            from auto_mosaic.src.env_config import EnvironmentConfig
            env_config = EnvironmentConfig()
            self.config = env_config.get_discord_config()
            logger.info("Discord auth: using environment configuration")
        
        self.token_manager = DiscordTokenManager()
        
        # Discord API設定
        self.client_id = self.config.get('client_id')
        self.client_secret = self.config.get('client_secret') 
        self.redirect_uri = self.config.get('redirect_uri', 'http://localhost:8000/callback')
        
        # デバッグ: 設定値の確認
        logger.debug(f"Discord config loaded: client_id={self.client_id}, redirect_uri={self.redirect_uri}")
        logger.debug(f"Config keys available: {list(self.config.keys()) if self.config else 'None'}")
        
        # デモ設定の検出と警告
        if self.client_id == "demo_client_id" or self.client_id is None:
            logger.warning("⚠️  Discord認証: デモ設定またはNone値が検出されました")
            logger.warning("   配布版では正常なDiscord認証情報が必要です")
            logger.warning("   暗号化設定ファイル(config/auth.dat)の復号化に失敗しているか、")
            logger.warning("   cryptographyライブラリが正しく含まれていない可能性があります")
        
        # 認証に使用する変数
        self.access_token: Optional[str] = None
        self.token_type: str = "Bearer"
        self.user_id: Optional[str] = None
        
        # レート制限対応
        self.last_role_check_time = 0
        self.role_check_cooldown = 60  # 1分間のクールダウン
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
        # 認証成功時間の管理（新機能）
        self.last_successful_auth_time = 0  # インスタンス固有
        self.auth_cache_duration = 600  # 10分間
        
        # クラス共有の成功時間も初期化
        if not hasattr(DiscordAuthAdapter, '_shared_last_successful_auth_time'):
            DiscordAuthAdapter._shared_last_successful_auth_time = 0
        if not hasattr(DiscordAuthAdapter, '_shared_last_role_check_time'):
            DiscordAuthAdapter._shared_last_role_check_time = 0
        if not hasattr(DiscordAuthAdapter, '_shared_consecutive_failures'):
            DiscordAuthAdapter._shared_consecutive_failures = 0
        
        # クラス共有の値を読み込み
        self.last_successful_auth_time = DiscordAuthAdapter._shared_last_successful_auth_time
        self.last_role_check_time = DiscordAuthAdapter._shared_last_role_check_time
        self.consecutive_failures = DiscordAuthAdapter._shared_consecutive_failures
        
        # HTTPセッションの初期化（堅牢なタイムアウト設定）
        self.session = requests.Session()
        # 全てのリクエストにデフォルトタイムアウトを設定
        self.session.request = lambda *args, **kwargs: requests.Session.request(
            self.session, *args, **{**kwargs, 'timeout': kwargs.get('timeout', (5, 10))}
        )
        
        # ギルド（サーバー）設定を読み込み
        self.GUILD_CONFIGS = self.config.get('guilds', [])
        
        # 初期化
        self.callback_server = None
        
        # 認証URLは動的に生成するため、ここでは設定値のみ保存
        self.auth_scopes = self.config.get("scopes", ["identify", "guilds", "guilds.members.read"])
    
    def _build_auth_url(self, redirect_uri: str) -> str:
        """動的リダイレクトURIを使用して認証URLを構築"""
        scope_string = '%20'.join(self.auth_scopes)
        return (
            f"https://discord.com/api/oauth2/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scope_string}"
        )
    
    def _load_persistent_cache(self):
        """永続化されたキャッシュを読み込み"""
        try:
            token_data = self.token_manager.load_token()
            if token_data and 'last_auth_success' in token_data:
                last_auth_success_str = token_data['last_auth_success']
                try:
                    last_auth_success = datetime.fromisoformat(last_auth_success_str)
                    age_seconds = (datetime.now() - last_auth_success).total_seconds()
                    
                    # キャッシュが有効な場合、メモリキャッシュも復元
                    if age_seconds < self.auth_cache_duration:
                        self.last_successful_auth_time = last_auth_success.timestamp()
                        DiscordAuthAdapter._shared_last_successful_auth_time = self.last_successful_auth_time
                        logger.debug(f"Discord auth: restored persistent cache (age: {age_seconds/60:.1f}min)")
                    else:
                        logger.debug(f"Discord auth: persistent cache expired ({age_seconds/60:.1f}min > {self.auth_cache_duration/60:.1f}min)")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Discord auth: failed to parse persistent cache: {e}")
        except Exception as e:
            logger.debug(f"Failed to load persistent cache: {e}")
    
    def _update_shared_cache(self):
        """共有キャッシュを更新"""
        DiscordAuthAdapter._shared_last_successful_auth_time = self.last_successful_auth_time
        DiscordAuthAdapter._shared_consecutive_failures = self.consecutive_failures
        DiscordAuthAdapter._shared_last_role_check_time = self.last_role_check_time

    def is_authenticated(self) -> bool:
        """認証状態をチェック（永続キャッシュ機能付き）"""
        try:
            current_time = time.time()
            
            # 共有キャッシュから最新の状態を取得
            self.last_successful_auth_time = DiscordAuthAdapter._shared_last_successful_auth_time
            self.consecutive_failures = DiscordAuthAdapter._shared_consecutive_failures
            self.last_role_check_time = DiscordAuthAdapter._shared_last_role_check_time
            
            # トークンの存在確認
            token_data = self.token_manager.load_token()
            if not token_data:
                logger.debug("Discord auth: no token found")
                return False
            
            self.access_token = token_data.get('access_token')
            self.token_type = token_data.get('token_type', 'Bearer')
            
            if not self.access_token:
                logger.debug("Discord auth: no access token")
                return False
            
            # 保存された認証成功時刻をチェック（永続キャッシュ）
            last_auth_success_str = token_data.get('last_auth_success')
            logger.debug(f"Discord auth: last_auth_success from file: {last_auth_success_str}")
            logger.debug(f"Discord auth: auth_cache_duration: {self.auth_cache_duration}s")
            
            # キャッシュは有効期間が短い場合のみ使用（1時間 -> 10分に短縮）
            cache_valid_duration = 600  # 10分
            
            if last_auth_success_str:
                try:
                    last_auth_success = datetime.fromisoformat(last_auth_success_str)
                    age_seconds = (datetime.now() - last_auth_success).total_seconds()
                    logger.debug(f"Discord auth: calculated age: {age_seconds:.1f}s")
                    
                    # 認証キャッシュが有効かつ短期間の場合のみスキップ
                    if age_seconds < cache_valid_duration:
                        logger.info(f"Discord auth: using cached success, skipping role check (last success: {age_seconds/60:.0f}min ago)")
                        self.last_successful_auth_time = last_auth_success.timestamp()
                        DiscordAuthAdapter._shared_last_successful_auth_time = self.last_successful_auth_time
                        return True
                    else:
                        logger.debug(f"Discord auth: cache expired ({age_seconds:.1f}s > {cache_valid_duration}s)")
                        # 期限切れキャッシュを削除
                        if 'last_auth_success' in token_data:
                            del token_data['last_auth_success']
                            self.token_manager.save_token(token_data)
                            logger.debug("Discord auth: expired cache cleared")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Discord auth: failed to parse last_auth_success: {e}")
            else:
                logger.debug("Discord auth: no last_auth_success found in token data")
            
            # メモリ内キャッシュもチェック（短期間のみ）
            if (self.last_successful_auth_time > 0 and 
                current_time - self.last_successful_auth_time < cache_valid_duration):
                cache_age = current_time - self.last_successful_auth_time
                logger.info(f"Discord auth: using memory cached success, skipping role check (age: {cache_age/60:.0f}min)")
                return True
            
            # 連続失敗回数が上限に達している場合
            if self.consecutive_failures >= self.max_consecutive_failures:
                logger.warning(f"Discord auth: too many consecutive failures ({self.consecutive_failures}/{self.max_consecutive_failures})")
                return False
            
            # クールダウンチェック
            if current_time - self.last_role_check_time < self.role_check_cooldown:
                # クールダウン中でも、最近成功していれば認証成功とみなす
                if (self.last_successful_auth_time > 0 and 
                    current_time - self.last_successful_auth_time < cache_valid_duration):
                    logger.debug(f"Discord auth: cooldown but using cached success")
                    return True
                logger.debug(f"Discord auth: rate limiting, skipping check (cooldown: {self.role_check_cooldown}s)")
                return False
            
            # ロールチェックを実行
            logger.info("Discord auth: performing role check (cache expired)")
            self.last_role_check_time = current_time
            DiscordAuthAdapter._shared_last_role_check_time = self.last_role_check_time
            result = self._check_user_roles()
            
            # 成功時の処理
            if result:
                self.consecutive_failures = 0
                self.last_successful_auth_time = current_time  # 成功時刻を記録
                
                # 共有キャッシュを更新
                self._update_shared_cache()
                
                # 永続キャッシュとして認証成功時刻を保存（重複チェック付き）
                try:
                    # 既存のlast_auth_successが古い場合のみ更新
                    current_success_str = token_data.get('last_auth_success')
                    should_update = True
                    
                    if current_success_str:
                        try:
                            current_success = datetime.fromisoformat(current_success_str)
                            # 1分以内の更新は避ける（重複保存防止）
                            if (datetime.now() - current_success).total_seconds() < 60:
                                should_update = False
                                logger.debug("Discord auth: skipping token update (recent success within 60s)")
                        except (ValueError, TypeError):
                            pass  # パースエラーの場合は更新する
                    
                    if should_update:
                        self.token_manager.save_auth_success()
                        logger.debug(f"Discord auth: auth success time updated in token file")
                    
                    cache_until = datetime.fromtimestamp(current_time + cache_valid_duration)
                    logger.debug(f"Discord auth: role check successful, cached for 10 minutes until {cache_until}")
                except Exception as e:
                    logger.warning(f"Failed to update auth success time: {e}")
            else:
                self.consecutive_failures += 1
                DiscordAuthAdapter._shared_consecutive_failures = self.consecutive_failures
                logger.warning(f"Discord auth: consecutive failures: {self.consecutive_failures}/{self.max_consecutive_failures}")
                
                # ロールチェック失敗時はトークンファイル自体を削除
                try:
                    # トークンファイルを完全に削除（無効なトークンでの再試行を防ぐ）
                    self.token_manager.clear_token()
                    logger.info("Discord auth: deleted token file due to role check failure (prevents API rate limiting)")
                    
                    # メモリキャッシュもリセット
                    self.last_successful_auth_time = 0
                    DiscordAuthAdapter._shared_last_successful_auth_time = 0
                    
                except Exception as e:
                    logger.warning(f"Failed to clear auth token after role check failure: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Discord authentication check failed: {e}")
            self.consecutive_failures += 1
            DiscordAuthAdapter._shared_consecutive_failures = self.consecutive_failures
            return False
    
    def authenticate(self) -> bool:
        """Discord認証を実行"""
        try:
            logger.info("Starting Discord authentication...")
            
            # コールバックサーバーを開始
            self.callback_server = DiscordCallbackServer()
            server_thread = threading.Thread(target=self.callback_server.start, daemon=True)
            server_thread.start()
            
            # サーバーが開始されるまで少し待機
            time.sleep(0.5)
            
            # 実際に使用されているポートを取得
            actual_port = self.callback_server.get_actual_port()
            if actual_port is None:
                logger.error("Failed to start callback server")
                logger.error("すべてのポート（8000-8009）が使用中です。他のアプリケーションを終了してから再試行してください。")
                logger.error("詳細は docs/DISCORD_SETUP_GUIDE.md を参照してください。")
                return False
                
            # 動的に認証URLを構築（実際のポートを使用）
            dynamic_redirect_uri = f"http://localhost:{actual_port}/callback"
            auth_url = self._build_auth_url(dynamic_redirect_uri)
            
            logger.info(f"🔗 Using dynamic redirect URI: {dynamic_redirect_uri}")
            logger.info(f"📊 Port selection details: preferred={self.callback_server.preferred_port}, actual={actual_port}")
            logger.info(f"🌐 Opening Discord auth URL: {auth_url}")
            
            # テスト用の詳細情報を出力
            if actual_port != 8000:
                logger.warning(f"⚠️  ポート{actual_port}を使用中（ポート8000は使用不可）")
                logger.info(f"💡 Discord Developer Portalで http://localhost:{actual_port}/callback が登録されているか確認してください")
            
            webbrowser.open(auth_url)
            
            # 認証コードを待機
            logger.info("Waiting for Discord auth code...")
            auth_code = self.callback_server.wait_for_code(timeout=300)  # 5分待機
            
            if not auth_code:
                logger.warning("Discord auth code not received within timeout")
                self._clear_all_auth_cache()  # 失敗時にキャッシュクリア
                return False
            
            logger.info("Discord auth code received, exchanging for token...")
            
            # トークンを取得
            if self._get_token(auth_code):
                # ロールチェック
                if self._check_user_roles():
                    # 認証が完全に成功した時のみ成功時刻を保存
                    self.last_successful_auth_time = time.time()
                    self.token_manager.save_auth_success()  # 永続キャッシュとして認証成功時刻を保存
                    logger.info("Discord authentication successful")
                    return True
                else:
                    logger.warning("Discord authentication failed: insufficient roles")
                    self._clear_all_auth_cache()  # ロール不足時にキャッシュクリア
                    return False
            else:
                logger.warning("Discord token exchange failed")
                self._clear_all_auth_cache()  # トークン取得失敗時にキャッシュクリア
                return False
                
        except Exception as e:
            logger.error(f"Discord authentication error: {e}")
            self._clear_all_auth_cache()  # 例外発生時にキャッシュクリア
            return False
        finally:
            if self.callback_server:
                self.callback_server.stop()
                
    def _clear_all_auth_cache(self):
        """認証キャッシュを完全にクリア"""
        try:
            # メモリキャッシュをクリア
            self.last_successful_auth_time = 0
            DiscordAuthAdapter._shared_last_successful_auth_time = 0
            
            # 永続キャッシュもクリア
            token_data = self.token_manager.load_token()
            if token_data and 'last_auth_success' in token_data:
                del token_data['last_auth_success']
                self.token_manager.save_token(token_data)
                logger.info("Discord auth: cleared all cached success data due to authentication failure")
                
        except Exception as e:
            logger.warning(f"Failed to clear auth cache: {e}")
    
    def _get_token(self, code: str) -> bool:
        """認証コードからトークンを取得"""
        try:
            # 動的なリダイレクトURIを使用（実際に使用されたポートを取得）
            if self.callback_server and self.callback_server.get_actual_port():
                dynamic_redirect_uri = f"http://localhost:{self.callback_server.get_actual_port()}/callback"
            else:
                # フォールバック（通常はここには来ないはず）
                dynamic_redirect_uri = self.redirect_uri
                
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': dynamic_redirect_uri
            }
            
            logger.debug(f"Token request using redirect_uri: {dynamic_redirect_uri}")
            
            response = self.session.post(
                'https://discord.com/api/oauth2/token',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=(5, 25)  # (connect_timeout, read_timeout)
            )
            
            if response.status_code != 200:
                logger.error(f"Discord token request failed: {response.status_code} - {response.text}")
                
                # デモ設定の問題を特に検出
                if self.client_id == "demo_client_id":
                    logger.error("❌ Discord認証エラー: デモ設定が使用されています")
                    logger.error("   これは配布版での設定読み込み問題を示しています")
                    logger.error("   解決方法:")
                    logger.error("   1. exe ファイルに cryptography ライブラリが含まれていない")
                    logger.error("   2. 暗号化設定ファイル (config/auth.dat) が破損している")
                    logger.error("   3. exe ファイルの再ビルドが必要")
                
                return False
            
            token_data = response.json()
            
            # トークンを保存
            self.token_manager.save_token(token_data)
            
            # インスタンス変数に設定
            self.access_token = token_data.get('access_token')
            self.token_type = token_data.get('token_type', 'Bearer')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to get Discord token: {e}")
            return False
    
    def _check_user_roles(self) -> bool:
        """複数サーバーでのユーザーロールをチェック（1回のみ、高速判定）"""
        if not self.access_token:
            logger.warning("No Discord access token available for role check")
            return False
        
        try:
            headers = {
                'Authorization': f'{self.token_type} {self.access_token}'
            }
            
            # レート制限検出フラグ
            rate_limited_count = 0
            total_guilds = len(self.GUILD_CONFIGS)
            
            # 各サーバーでロールチェックを実行（リトライなし）
            for guild_config in self.GUILD_CONFIGS:
                guild_id = guild_config["guild_id"]
                required_roles = guild_config["required_roles"]
                guild_name = guild_config["name"]
                
                logger.info(f"Checking roles in guild: {guild_name} ({guild_id})")
                
                try:
                    # ユーザーのメンバー情報を取得（接続タイムアウトとリードタイムアウトを分離）
                    # connect_timeout: 接続確立のタイムアウト（短め）
                    # read_timeout: データ読み取りのタイムアウト
                    response = self.session.get(
                        f'https://discord.com/api/users/@me/guilds/{guild_id}/member',
                        headers=headers,
                        timeout=(5, 10)  # (connect_timeout, read_timeout)
                    )
                    
                    if response.status_code == 200:
                        member_data = response.json()
                        user_role_ids = set(member_data.get('roles', []))
                        required_role_ids = set(required_roles)
                        
                        # いずれかの必要なロールを持っているかチェック
                        has_required_role = bool(user_role_ids & required_role_ids)
                        
                        if has_required_role:
                            # 成功したロールを特定
                            matched_roles = user_role_ids & required_role_ids
                            
                            logger.info(f"✅ Discord role check passed in {guild_name}")
                            logger.info(f"   🎯 Successful roles: {matched_roles}")
                            logger.info(f"   👤 User roles: {len(user_role_ids)} total")
                            logger.info(f"   📋 Required roles: {len(required_role_ids)} total")
                            return True
                        else:
                            logger.info(f"❌ No required roles in {guild_name}")
                            logger.info(f"   👤 User has: {user_role_ids if user_role_ids else 'No roles'}")
                            logger.info(f"   📋 Required: {required_role_ids}")
                            
                    elif response.status_code == 404:
                        logger.info(f"❌ User is not a member of {guild_name}")
                        
                    elif response.status_code == 429:
                        # レート制限の場合 - より正確な情報を使用
                        retry_after = response.headers.get('Retry-After', 'unknown')
                        reset_after = response.headers.get('X-RateLimit-Reset-After', 'unknown')
                        
                        # レスポンスボディからも情報を取得
                        try:
                            response_json = response.json()
                            body_retry_after = response_json.get('retry_after', 'unknown')
                        except:
                            body_retry_after = 'unknown'
                        
                        # より信頼できる値を選択（レスポンスボディを最優先）
                        if body_retry_after != 'unknown' and body_retry_after != 'unknown':
                            try:
                                # レスポンスボディの値を数値として検証
                                float(body_retry_after)
                                actual_delay = body_retry_after
                                source = "response body"
                            except (ValueError, TypeError):
                                if reset_after != 'unknown':
                                    actual_delay = reset_after
                                    source = "X-RateLimit-Reset-After"
                                else:
                                    actual_delay = retry_after
                                    source = "Retry-After header"
                        elif reset_after != 'unknown':
                            actual_delay = reset_after
                            source = "X-RateLimit-Reset-After"
                        else:
                            actual_delay = retry_after
                            source = "Retry-After header"
                        
                        logger.warning(f"❌ Rate limited for {guild_name}")
                        logger.warning(f"   Retry-After header: {retry_after}s")
                        logger.warning(f"   X-RateLimit-Reset-After: {reset_after}s")
                        logger.warning(f"   Response body retry_after: {body_retry_after}s")
                        logger.warning(f"   Using: {actual_delay}s (from {source})")
                        
                        rate_limited_count += 1
                        
                    elif response.status_code == 401:
                        logger.error(f"❌ Authentication failed for {guild_name} - token may be invalid")
                        # トークンが無効な場合は永続キャッシュをクリア
                        try:
                            token_data = self.token_manager.load_token()
                            if token_data and 'last_auth_success' in token_data:
                                del token_data['last_auth_success']
                                self.token_manager.save_token(token_data)
                                logger.info("Discord auth: cleared cached success due to invalid token (401)")
                            
                            # メモリキャッシュもリセット
                            self.last_successful_auth_time = 0
                            DiscordAuthAdapter._shared_last_successful_auth_time = 0
                            
                        except Exception as e:
                            logger.warning(f"Failed to clear auth cache after 401 error: {e}")
                        
                        return False  # 認証エラーの場合は即座に失敗
                        
                    else:
                        logger.warning(f"❌ Failed to check membership in {guild_name}: HTTP {response.status_code}")
                        # ログに詳細を記録するが、他のサーバーもチェックを続行
                        logger.debug(f"Response details: {response.text[:200]}...")
                        
                except requests.exceptions.Timeout as e:
                    logger.warning(f"❌ Timeout checking membership in {guild_name}")
                    logger.warning(f"   Timeout details: {e}")
                    logger.warning(f"   This prevents long application freezes during network issues")
                    
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"❌ Connection error checking {guild_name}: {e}")
                    logger.warning(f"   Network connectivity issue or DNS resolution failure")
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"❌ Network error checking {guild_name}: {e}")
                    
                except Exception as e:
                    logger.error(f"❌ Unexpected error checking {guild_name}: {e}")
            
            # レート制限が発生している場合の特別処理
            if rate_limited_count > 0:
                logger.error(f"🚨 {rate_limited_count}/{total_guilds} guilds are rate limited!")
                logger.error("⚠️  This may indicate excessive API usage or temporary Discord restrictions.")
                
                # 開発者モードまたは緊急時の一時的なバイパス
                if self._is_emergency_bypass_enabled():
                    logger.warning(f"🔧 Emergency bypass enabled - allowing authentication despite {rate_limited_count} rate limited guild(s)")
                    return True
            
            logger.warning("❌ Discord role check failed in all configured guilds")
            return False
            
        except Exception as e:
            logger.error(f"Discord role check error: {e}")
            return False
    
    def _is_emergency_bypass_enabled(self) -> bool:
        """緊急時のバイパスが有効かチェック"""
        try:
            # 環境変数または設定ファイルでバイパスを制御
            import os
            
            # 1. 環境変数チェック
            if os.getenv('DISCORD_EMERGENCY_BYPASS') == 'true':
                logger.info("🔧 Emergency bypass enabled via environment variable")
                return True
            
            # 2. 開発者モードファイルのチェック
            from pathlib import Path
            bypass_file = Path("config/discord_emergency_bypass.txt")
            if bypass_file.exists():
                logger.info("🔧 Emergency bypass enabled via bypass file")
                return True
            
            # 3. 開発者モードの設定ファイルチェック
            dev_mode_file = Path("config/developer_mode.flag")
            if dev_mode_file.exists():
                logger.info("🔧 Emergency bypass enabled via developer mode")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking emergency bypass: {e}")
            return False
    
    def clear_authentication(self) -> None:
        """認証情報をクリア"""
        try:
            # トークンファイルから永続キャッシュも削除
            token_data = self.token_manager.load_token()
            if token_data and 'last_auth_success' in token_data:
                del token_data['last_auth_success']
                self.token_manager.save_token(token_data)
                logger.debug("Discord auth: cleared persistent cache from token file")
            
            self.token_manager.clear_token()
            self.access_token = None
            self.token_type = None
            self.consecutive_failures = 0
            self.last_role_check_time = 0
            self.last_successful_auth_time = 0  # 認証キャッシュもクリア
            
            # 共有キャッシュもクリア
            DiscordAuthAdapter._shared_last_successful_auth_time = 0
            DiscordAuthAdapter._shared_consecutive_failures = 0
            DiscordAuthAdapter._shared_last_role_check_time = 0
            
            logger.info("Discord authentication cleared")
        except Exception as e:
            logger.error(f"Failed to clear Discord authentication: {e}")

    def reset_failure_count(self) -> None:
        """失敗カウンターをリセット（force_dialog用）"""
        self.consecutive_failures = 0
        DiscordAuthAdapter._shared_consecutive_failures = 0
        logger.debug("Discord auth: failure count reset") 