"""
統合認証マネージャー
既存の月次パスワード認証とDiscord認証を統一インターフェースで管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from pathlib import Path

from auto_mosaic.src.utils import logger
from auto_mosaic.src.auth_config import AuthConfig, AuthMethod
from auto_mosaic.src.discord_auth_adapter import DiscordAuthAdapter

# 既存の認証システムをインポート
from auto_mosaic.src.auth import authenticate_user as monthly_authenticate_user, MonthlyAuth

class AuthenticationManager:
    """統合認証マネージャー"""
    
    def __init__(self):
        self.auth_config = AuthConfig()
        self.discord_auth = DiscordAuthAdapter()
        self.monthly_auth = MonthlyAuth()
        self._alternative_method = None  # 開発者モードでの代替認証方式
        self._error_dialog_shown = False  # エラーダイアログ表示済みフラグ
        
        # 開発者モード時の設定を自動適用
        self.auth_config.ensure_developer_mode_settings()
        
        logger.info("Authentication manager initialized")
    
    def authenticate(self, parent=None, force_dialog: bool = False) -> bool:
        """
        設定された認証方式で認証を実行
        
        Args:
            parent: 親ウィンドウ
            force_dialog: 認証ダイアログを強制表示するか
            
        Returns:
            bool: 認証が成功したかどうか
        """
        try:
            # エラーダイアログフラグをリセット
            self._error_dialog_shown = False
            
            # 現在の認証方式を取得
            auth_method = self.auth_config.get_auth_method()
            
            logger.info(f"Starting authentication with method: {auth_method.value}")
            
            if auth_method == AuthMethod.MONTHLY_PASSWORD:
                result = self._authenticate_monthly_password(parent, force_dialog)
            elif auth_method == AuthMethod.DISCORD:
                result = self._authenticate_discord(parent, force_dialog)
            else:
                logger.error(f"Unknown authentication method: {auth_method}")
                return False
            
            # 認証成功時の処理
            if result:
                self.auth_config.set_last_successful_method(auth_method)
                logger.info(f"Authentication successful with method: {auth_method.value}")
            else:
                logger.warning(f"Authentication failed with method: {auth_method.value}")
                
                # 認証に失敗した場合、別の方式を試すかユーザーに確認
                if self._should_try_alternative_method(parent, auth_method):
                    return self._try_alternative_authentication(parent)
            
            return result
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _authenticate_monthly_password(self, parent=None, force_dialog: bool = False) -> bool:
        """月次パスワード認証を実行"""
        try:
            logger.debug("Executing monthly password authentication")
            
            if not force_dialog:
                # まず既存の認証状態をチェック
                if self.monthly_auth.is_already_authenticated_this_month():
                    logger.info("Monthly password: already authenticated this month")
                    return True
            
            # 認証ダイアログを表示
            return monthly_authenticate_user(parent, force_dialog)
            
        except Exception as e:
            logger.error(f"Monthly password authentication error: {e}")
            return False
    
    def _authenticate_discord(self, parent=None, force_dialog: bool = False) -> bool:
        """Discord認証を実行"""
        try:
            logger.debug("Executing Discord authentication")
            logger.debug(f"force_dialog: {force_dialog}")
            
            # force_dialogの場合は失敗カウンターをリセット
            if force_dialog:
                self.discord_auth.reset_failure_count()
                logger.debug("Force dialog is True, reset failure count and skipping authentication status check")
            else:
                # まず既存の認証状態をチェック
                is_already_authenticated = self.discord_auth.is_authenticated()
                logger.debug(f"Discord authentication status check: {is_already_authenticated}")
                
                if is_already_authenticated:
                    logger.info("Discord: already authenticated")
                    return True
            
            logger.debug("Proceeding to show Discord auth dialog")
            # Discord認証ダイアログを表示
            result = self._show_discord_auth_dialog(parent)
            
            # 認証失敗時はキャッシュを確実にクリア
            if not result:
                logger.warning("Discord authentication failed, clearing all cache")
                try:
                    # Discord認証アダプターのキャッシュクリア機能を呼び出し
                    if hasattr(self.discord_auth, '_clear_all_auth_cache'):
                        self.discord_auth._clear_all_auth_cache()
                    else:
                        # フォールバック: 手動でキャッシュクリア
                        self.discord_auth.last_successful_auth_time = 0
                        if hasattr(self.discord_auth, '_shared_last_successful_auth_time'):
                            self.discord_auth.__class__._shared_last_successful_auth_time = 0
                        logger.info("Discord auth cache cleared (fallback method)")
                except Exception as cache_clear_error:
                    logger.error(f"Failed to clear Discord auth cache: {cache_clear_error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Discord authentication error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # 例外発生時もキャッシュクリア
            try:
                if hasattr(self.discord_auth, '_clear_all_auth_cache'):
                    self.discord_auth._clear_all_auth_cache()
            except:
                pass
            
            return False
    
    def _show_discord_auth_dialog(self, parent=None) -> bool:
        """Discord認証ダイアログを表示"""
        try:
            logger.debug("Creating Discord auth dialog...")
            dialog = DiscordAuthDialog(parent, self.discord_auth)
            logger.debug("Discord auth dialog created, showing...")
            result = dialog.show()
            logger.debug(f"Discord auth dialog result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Discord auth dialog error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _should_try_alternative_method(self, parent, current_method: AuthMethod) -> bool:
        """認証失敗時に別の方式を試すかユーザーに確認"""
        # 認証方式切り替えが許可されていない場合（一般配布版）
        if not self.auth_config.is_method_switching_allowed():
            logger.info("Authentication method switching not allowed for this user")
            # 一般配布版では認証失敗時に代替方式を提案しない
            messagebox.showerror(
                "認証失敗",
                f"認証に失敗しました。\n\n"
                f"適切な認証情報を確認してアプリケーションを再起動してください。",
                parent=parent
            )
            self._error_dialog_shown = True  # エラーダイアログ表示済みをマーク
            return False
        
        # 最後に成功した方式があれば、それを提案
        last_successful = self.auth_config.get_last_successful_method()
        if last_successful and last_successful != current_method:
            alternative_name = "月次パスワード認証" if last_successful == AuthMethod.MONTHLY_PASSWORD else "Discord認証"
            current_name = "月次パスワード認証" if current_method == AuthMethod.MONTHLY_PASSWORD else "Discord認証"
            
            result = messagebox.askyesno(
                "認証失敗",
                f"{current_name}に失敗しました。\n\n"
                f"前回成功した{alternative_name}を試しますか？",
                parent=parent
            )
            
            return result
        
        # 開発者モードでは、他の認証方式を提案
        if self.auth_config.is_developer_mode():
            alternative_method = AuthMethod.MONTHLY_PASSWORD if current_method == AuthMethod.DISCORD else AuthMethod.DISCORD
            alternative_name = "月次パスワード認証" if alternative_method == AuthMethod.MONTHLY_PASSWORD else "Discord認証"
            current_name = "月次パスワード認証" if current_method == AuthMethod.MONTHLY_PASSWORD else "Discord認証"
            
            result = messagebox.askyesno(
                "認証失敗（開発者モード）",
                f"{current_name}に失敗しました。\n\n"
                f"代替の{alternative_name}を試しますか？\n"
                f"（開発者モード機能）",
                parent=parent
            )
            
            if result:
                # 代替認証を記録
                self._alternative_method = alternative_method
            
            return result
        
        return False
    
    def _try_alternative_authentication(self, parent) -> bool:
        """代替の認証方式を試行"""
        # 開発者モードで設定された代替方式を使用
        if hasattr(self, '_alternative_method'):
            alternative_method = self._alternative_method
            logger.info(f"Trying alternative authentication method (dev mode): {alternative_method.value}")
            
            if alternative_method == AuthMethod.MONTHLY_PASSWORD:
                return self._authenticate_monthly_password(parent, force_dialog=True)
            elif alternative_method == AuthMethod.DISCORD:
                return self._authenticate_discord(parent, force_dialog=True)
        
        # 通常の代替認証（最後に成功した方式）
        last_successful = self.auth_config.get_last_successful_method()
        if last_successful:
            logger.info(f"Trying alternative authentication method: {last_successful.value}")
            
            if last_successful == AuthMethod.MONTHLY_PASSWORD:
                return self._authenticate_monthly_password(parent, force_dialog=True)
            elif last_successful == AuthMethod.DISCORD:
                return self._authenticate_discord(parent, force_dialog=True)
        
        return False
    
    def is_authenticated(self) -> bool:
        """現在の認証状態をチェック"""
        try:
            auth_method = self.auth_config.get_auth_method()
            
            if auth_method == AuthMethod.MONTHLY_PASSWORD:
                return self.monthly_auth.is_already_authenticated_this_month()
            elif auth_method == AuthMethod.DISCORD:
                return self.discord_auth.is_authenticated()
            
            return False
            
        except Exception as e:
            logger.error(f"Authentication check error: {e}")
            return False
    
    def clear_authentication(self) -> None:
        """認証情報をクリア"""
        try:
            logger.info("Clearing all authentication data")
            
            # 月次パスワード認証をクリア
            self.monthly_auth.clear_authentication_state()
            
            # Discord認証をクリア
            self.discord_auth.clear_authentication()
            
            logger.info("All authentication data cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear authentication: {e}")
    
    def get_current_auth_method(self) -> AuthMethod:
        """現在の認証方式を取得"""
        return self.auth_config.get_auth_method()
    
    def set_auth_method(self, method: AuthMethod) -> bool:
        """認証方式を設定"""
        return self.auth_config.set_auth_method(method)
    
    def show_auth_method_selection_dialog(self, parent=None) -> Optional[AuthMethod]:
        """認証方式選択ダイアログを表示"""
        try:
            dialog = AuthMethodSelectionDialog(parent, self.auth_config)
            return dialog.show()
            
        except Exception as e:
            logger.error(f"Auth method selection dialog error: {e}")
            return None
    
    def has_shown_error_dialog(self) -> bool:
        """エラーダイアログが既に表示されたかどうかを確認"""
        return self._error_dialog_shown

class DiscordAuthDialog:
    """Discord認証ダイアログ"""
    
    def __init__(self, parent, discord_auth: DiscordAuthAdapter):
        self.parent = parent
        self.discord_auth = discord_auth
        self.dialog = None
        self.result = False
        self.auth_in_progress = False
        self.auth_thread_completed = False  # 認証スレッドの完了状態を追跡
        self.timeout_seconds = 30  # 30秒でタイムアウト
        self.start_time = None
        self.timeout_timer_id = None  # タイマーIDを追跡
    
    def show(self) -> bool:
        """ダイアログを表示（タイムアウト付き）"""
        try:
            import time
            self.start_time = time.time()
            
            logger.debug("Creating Discord auth dialog UI...")
            self._create_dialog()
            
            logger.debug("Setting up dialog modal properties...")
            # ダイアログを表示
            self.dialog.lift()  # ダイアログを前面に
            self.dialog.attributes('-topmost', True)  # 最前面に表示
            try:
                self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))  # 100ms後に最前面解除
            except Exception as e:
                logger.debug(f"Error setting topmost attribute: {e}")
            
            self.dialog.grab_set()
            self.dialog.focus_force()
            
            # ダイアログが確実に表示されるまで少し待機
            self.dialog.update_idletasks()
            
            # ダイアログが正常に表示されているかチェック
            self.dialog.after(500, self._check_dialog_visibility)
            
            # タイムアウトチェックを開始
            self._start_timeout_check()
            
            logger.debug("Waiting for dialog window...")
            # ダイアログが閉じられるまで待機
            self.dialog.wait_window()
            
            logger.debug(f"Dialog closed with result: {self.result}")
            return self.result
            
        except Exception as e:
            logger.error(f"Discord auth dialog show error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _create_dialog(self):
        """ダイアログを作成"""
        logger.debug("Creating Toplevel dialog window...")
        self.dialog = tk.Toplevel(self.parent)
        
        logger.debug("Setting dialog properties...")
        self.dialog.title("Discord認証")
        self.dialog.geometry("450x300")
        self.dialog.resizable(False, False)
        
        # ダイアログを中央に配置
        self.dialog.transient(self.parent)
        
        logger.debug("Centering dialog...")
        # ダイアログを画面中央に配置
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        logger.debug("Creating dialog components...")
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🔐 Discord認証", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 説明テキスト
        desc_text = tk.Text(main_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        desc_content = """Discord認証を開始します。

手順:
1. 「Discord認証開始」ボタンをクリック
2. ブラウザでDiscordの認証ページが開きます
3. Discordアカウントでログインし、アプリケーションを承認
4. 認証が完了すると自動的にこのダイアログが閉じます

注意事項:
• 認証には有効なDiscordアカウントが必要です
• 指定されたDiscordサーバーのメンバーである必要があります
• 適切なロールが割り当てられている必要があります"""
        
        desc_text.config(state=tk.NORMAL)
        desc_text.insert("1.0", desc_content)
        desc_text.config(state=tk.DISABLED)
        
        # 進行状況表示
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack(pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.auth_button = ttk.Button(button_frame, text="Discord認証開始", 
                                     command=self._start_discord_auth)
        self.auth_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="キャンセル", 
                  command=self._cancel).pack(side=tk.RIGHT)
        
        logger.debug("Discord auth dialog creation completed")
    
    def _start_discord_auth(self):
        """Discord認証を開始"""
        logger.debug("Start Discord auth button clicked")
        
        if self.auth_in_progress:
            logger.debug("Authentication already in progress, ignoring click")
            return
        
        logger.debug("Setting auth in progress state...")
        self.auth_in_progress = True
        self.auth_button.config(state=tk.DISABLED)
        self.status_label.config(text="認証を開始しています...", foreground="blue")
        
        # 別スレッドで認証を実行
        logger.debug("Starting Discord authentication thread...")
        import threading
        auth_thread = threading.Thread(target=self._authenticate_discord_thread, daemon=True)
        auth_thread.start()
        
        # 進行状況をチェック
        logger.debug("Starting progress check timer...")
        self.dialog.after(1000, self._check_auth_progress)
    
    def _authenticate_discord_thread(self):
        """Discord認証を別スレッドで実行"""
        try:
            # Discord認証ダイアログ開始時に失敗カウントをリセット
            self.discord_auth.reset_failure_count()
            logger.debug("Discord auth dialog: reset failure count before authentication")
            
            self.result = self.discord_auth.authenticate()
        except Exception as e:
            logger.error(f"Discord authentication thread error: {e}")
            self.result = False
        finally:
            # 認証スレッドの完了をマーク
            self.auth_thread_completed = True
            logger.debug(f"Discord auth thread completed with result: {self.result}")
    
    def _check_auth_progress(self):
        """認証の進行状況をチェック"""
        if not self.auth_in_progress:
            return
        
        # 認証スレッドの結果のみをチェック（追加の認証処理を避ける）
        if self.auth_thread_completed and self.result:
            self.status_label.config(text="認証が完了しました！", foreground="green")
            self.auth_in_progress = False
            self.dialog.after(1000, self._close_dialog)
            return
        
        # 認証スレッドが完了した場合の処理
        if self.auth_thread_completed:
            if self.result:
                # 成功した場合（既に上でチェック済みなので、ここには来ないはず）
                self.status_label.config(text="認証が完了しました！", foreground="green")
                self.auth_in_progress = False
                self.dialog.after(1000, self._close_dialog)
            else:
                # 失敗した場合は即座に終了
                logger.warning("Discord auth thread completed with failure, stopping progress check")
                self.status_label.config(text="認証に失敗しました（必要なロールがありません）", foreground="red")
                self.auth_in_progress = False
                self.dialog.after(3000, self._close_dialog)
            return
        
        # 連続失敗回数が上限に達した場合も即座に停止
        if hasattr(self.discord_auth, 'consecutive_failures') and \
           self.discord_auth.consecutive_failures >= self.discord_auth.max_consecutive_failures:
            logger.warning(f"Discord auth progress check: max failures reached ({self.discord_auth.consecutive_failures}/{self.discord_auth.max_consecutive_failures})")
            self.status_label.config(text="認証に失敗しました（必要なロールがありません）", foreground="red")
            self.result = False
            self.auth_in_progress = False
            self.dialog.after(3000, self._close_dialog)
            return
        
        # まだ進行中の場合は再度チェック（頻度を下げる）
        self.dialog.after(3000, self._check_auth_progress)  # 1秒から3秒に変更
    
    def _close_dialog(self):
        """ダイアログを閉じる"""
        self.auth_in_progress = False
        
        # タイマーをキャンセル
        if self.timeout_timer_id and self.dialog:
            try:
                self.dialog.after_cancel(self.timeout_timer_id)
                self.timeout_timer_id = None
            except Exception as e:
                logger.debug(f"Error canceling timeout timer: {e}")
        
        if self.dialog:
            try:
                self.dialog.destroy()
            except Exception as e:
                logger.debug(f"Error destroying dialog: {e}")
            finally:
                self.dialog = None
    
    def _check_dialog_visibility(self):
        """ダイアログの可視性をチェック"""
        try:
            if self.dialog and self.dialog.winfo_exists():
                is_visible = self.dialog.winfo_viewable()
                is_mapped = self.dialog.winfo_ismapped()
                logger.debug(f"Dialog visibility check: visible={is_visible}, mapped={is_mapped}")
                
                if not is_visible or not is_mapped:
                    logger.warning("Dialog is not visible, attempting to show...")
                    self.dialog.deiconify()
                    self.dialog.lift()
                    self.dialog.focus_force()
            else:
                logger.error("Dialog does not exist during visibility check")
        except Exception as e:
            logger.error(f"Dialog visibility check error: {e}")
    
    def _start_timeout_check(self):
        """タイムアウトチェックを開始"""
        logger.debug(f"Starting timeout check ({self.timeout_seconds} seconds)")
        if self.dialog and self.dialog.winfo_exists():
            self.timeout_timer_id = self.dialog.after(1000, self._check_timeout)  # 1秒ごとにチェック
    
    def _check_timeout(self):
        """タイムアウトをチェック"""
        try:
            if not self.dialog or not self.dialog.winfo_exists():
                self.timeout_timer_id = None
                return
            
            import time
            elapsed = time.time() - self.start_time
            remaining = self.timeout_seconds - elapsed
            
            if elapsed >= self.timeout_seconds:
                logger.warning(f"Discord auth dialog timeout after {self.timeout_seconds} seconds")
                self.status_label.config(text="タイムアウトしました。ダイアログを閉じます...", foreground="red")
                self.timeout_timer_id = self.dialog.after(2000, self._timeout_close)  # 2秒後に閉じる
            else:
                # まだタイムアウトしていない場合は、ステータスに残り時間を表示
                if not self.auth_in_progress:
                    self.status_label.config(text=f"タイムアウトまで {int(remaining)} 秒", foreground="gray")
                
                # 次のチェックをスケジュール
                self.timeout_timer_id = self.dialog.after(1000, self._check_timeout)
        except Exception as e:
            # ダイアログが破棄された場合などのエラーを静かに処理
            logger.debug(f"Timeout check error (dialog may be destroyed): {e}")
            self.timeout_timer_id = None
    
    def _timeout_close(self):
        """タイムアウトによりダイアログを閉じる"""
        logger.debug("Closing dialog due to timeout")
        self.auth_in_progress = False
        self.result = False
        
        # タイマーをクリア
        self.timeout_timer_id = None
        
        if self.dialog:
            try:
                self.dialog.destroy()
            except Exception as e:
                logger.debug(f"Error destroying dialog on timeout: {e}")
            finally:
                self.dialog = None
    
    def _cancel(self):
        """認証をキャンセル"""
        logger.debug("User cancelled authentication")
        self.auth_in_progress = False
        self.result = False
        
        # タイマーをキャンセル
        if self.timeout_timer_id and self.dialog:
            try:
                self.dialog.after_cancel(self.timeout_timer_id)
                self.timeout_timer_id = None
            except Exception as e:
                logger.debug(f"Error canceling timeout timer: {e}")
        
        if self.dialog:
            try:
                self.dialog.destroy()
            except Exception as e:
                logger.debug(f"Error destroying dialog: {e}")
            finally:
                self.dialog = None

class AuthMethodSelectionDialog:
    """認証方式選択ダイアログ"""
    
    def __init__(self, parent, auth_config: AuthConfig):
        self.parent = parent
        self.auth_config = auth_config
        self.dialog = None
        self.result = None
        self.selected_method = None
    
    def show(self) -> Optional[AuthMethod]:
        """ダイアログを表示"""
        try:
            logger.debug("Creating auth method selection dialog...")
            self._create_dialog()
            
            logger.debug("Dialog created, setting grab and focus...")
            # ダイアログを表示
            self.dialog.grab_set()
            self.dialog.focus_force()
            
            # デバッグ情報
            logger.debug(f"Dialog state: visible={self.dialog.winfo_viewable()}, mapped={self.dialog.winfo_ismapped()}")
            
            # ダイアログが閉じられるまで待機
            logger.debug("Starting wait_window...")
            self.dialog.wait_window()
            
            logger.debug(f"Dialog closed, result: {self.result}")
            return self.result
            
        except Exception as e:
            logger.error(f"Auth method selection dialog show error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_dialog(self):
        """ダイアログを作成"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("認証方式の選択")
        self.dialog.geometry("400x250")
        self.dialog.resizable(False, False)
        
        # ダイアログを中央に配置
        self.dialog.transient(self.parent)
        
        # ダイアログを最前面に表示
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        try:
            self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        except Exception as e:
            logger.debug(f"Error setting topmost attribute: {e}")
        
        # 画面中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (250 // 2)
        self.dialog.geometry(f"400x250+{x}+{y}")
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="認証方式の選択", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 現在の設定を取得
        current_method = self.auth_config.get_auth_method()
        
        # ラジオボタン変数
        self.method_var = tk.StringVar(value=current_method.value)
        
        # 認証方式の選択
        methods_frame = ttk.LabelFrame(main_frame, text="認証方式", padding="10")
        methods_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Radiobutton(methods_frame, text="月次パスワード認証 (従来方式)", 
                       variable=self.method_var, 
                       value=AuthMethod.MONTHLY_PASSWORD.value).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(methods_frame, text="Discord認証 (新方式)", 
                       variable=self.method_var, 
                       value=AuthMethod.DISCORD.value).pack(anchor=tk.W, pady=2)
        
        # 説明テキスト
        desc_label = ttk.Label(main_frame, 
                              text="認証方式は後からでも変更できます。",
                              foreground="gray")
        desc_label.pack(pady=(0, 20))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="適用", 
                  command=self._apply).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="キャンセル", 
                  command=self._cancel).pack(side=tk.RIGHT)
    
    def _apply(self):
        """設定を適用"""
        try:
            method_str = self.method_var.get()
            method = AuthMethod(method_str)
            
            if self.auth_config.set_auth_method(method):
                self.result = method
                messagebox.showinfo("設定完了", 
                                  f"認証方式を「{self._get_method_display_name(method)}」に変更しました。",
                                  parent=self.dialog)
            else:
                messagebox.showerror("エラー", 
                                   "認証方式の設定に失敗しました。",
                                   parent=self.dialog)
                return
            
            if self.dialog:
                self.dialog.destroy()
                
        except Exception as e:
            logger.error(f"Apply auth method error: {e}")
            messagebox.showerror("エラー", 
                               f"設定の適用中にエラーが発生しました: {e}",
                               parent=self.dialog)
    
    def _cancel(self):
        """キャンセル"""
        self.result = None
        if self.dialog:
            self.dialog.destroy()
    
    def _get_method_display_name(self, method: AuthMethod) -> str:
        """認証方式の表示名を取得"""
        if method == AuthMethod.MONTHLY_PASSWORD:
            return "月次パスワード認証"
        elif method == AuthMethod.DISCORD:
            return "Discord認証"
        else:
            return str(method.value)

# 後方互換性のための関数
def authenticate_user(parent=None, force_auth_dialog=False) -> bool:
    """
    統合認証システムを使用してユーザーを認証
    既存のauth.pyのauthenticate_user関数と互換性を保つ
    """
    try:

        # 認証開始時にエラーダイアログフラグをクリア
        _clear_error_dialog_flag()
        
        auth_manager = AuthenticationManager()
        result = auth_manager.authenticate(parent, force_auth_dialog)
        
        # 認証失敗時に、AuthenticationManagerでエラーダイアログが表示された場合はフラグをセット
        if not result and auth_manager.has_shown_error_dialog():
            _set_error_dialog_shown()
        
        return result
    except Exception as e:
        logger.error(f"Integrated authentication error: {e}")
        # フォールバックとして既存の月次認証を使用
        return monthly_authenticate_user(parent, force_auth_dialog)

# エラーダイアログ表示状態をファイルで管理
import tempfile
import os

def _get_error_dialog_flag_file():
    """エラーダイアログ表示フラグファイルのパスを取得"""
    return os.path.join(tempfile.gettempdir(), "auto_mosaic_error_dialog_shown.flag")

def _set_error_dialog_shown():
    """エラーダイアログが表示されたことをファイルに記録"""
    try:
        flag_file = _get_error_dialog_flag_file()
        with open(flag_file, 'w') as f:
            f.write("1")
        logger.debug(f"Error dialog flag set: {flag_file}")
    except Exception as e:
        logger.error(f"Failed to set error dialog flag: {e}")

def _clear_error_dialog_flag():
    """エラーダイアログフラグをクリア"""
    try:
        flag_file = _get_error_dialog_flag_file()
        if os.path.exists(flag_file):
            os.remove(flag_file)
            logger.debug(f"Error dialog flag cleared: {flag_file}")
        else:
            logger.debug(f"Error dialog flag already clear: {flag_file}")
    except Exception as e:
        logger.error(f"Failed to clear error dialog flag: {e}")

def has_shown_auth_error_dialog() -> bool:
    """最後の認証でエラーダイアログが表示されたかどうかを確認"""
    try:
        flag_file = _get_error_dialog_flag_file()
        result = os.path.exists(flag_file)
        logger.debug(f"Error dialog flag check: {result} (file: {flag_file})")
        return result
    except Exception as e:
        logger.error(f"Failed to check error dialog flag: {e}")
        return False 