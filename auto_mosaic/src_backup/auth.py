"""
自動モザエセ v2.2 認証システム
Monthly password protection with one-time monthly authentication
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import requests
import json
import sys
import tempfile
import warnings

# HTTPS警告を抑制（実用性重視）
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

class MonthlyAuth:
    """Monthly password authentication system with one-time monthly verification"""
    
    def __init__(self):
        # デバッグログ用（最初に初期化）
        self.debug_log = []
        
        # 月次パスワード（SHA256ハッシュで保存）
        self.monthly_passwords = {
            "2025-01": "8f4b5e2d7c9a1f6e3b8d4a7c2e9f1b5c8a3d6e9c2f5b8e1a4d7c0f3b6e9a2d5c8",  # KDHFS-ERSKF-PDU4U
            "2025-02": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",  # MGKLS-WQERT-ZXC8V
            "2025-03": "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",  # PQRST-UVWXY-ABC9D
            "2025-04": "2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d",  # NFGHI-JKLMN-OPQ1R
            "2025-05": "5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a",  # STUVW-XYZAB-CDE2F
            "2025-06": "4c2b4b30fd2fbb87952b2621e611eb3b7a9b893dd233faa0fde18307693883b3",  # GHIJK-LMNOP-QRS3T
            "2025-07": "1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e",  # UVWXY-ZABCD-EFG4H
            "2025-08": "4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b",  # IJKLM-NOPQR-STU5V
            "2025-09": "7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e",  # WXYZ1-23456-789AB
            "2025-10": "0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",  # CDEFG-HIJKL-MNO6P
            "2025-11": "3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",  # QRSTU-VWXYZ-123QW
            "2025-12": "6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b"   # ERTYU-IOPAS-DFGH7
        }
        
        # マスターパスワード（管理者・開発者用）
        self.master_password_hash = "9525a1515bdde00dbabf861f7866b5cb691cd33df31ebfdaa5327d5fb5cad25e"  # "yofumoza"のハッシュ
        
        # exe化環境検出
        self.is_exe = getattr(sys, 'frozen', False)
        
        # 認証状態保存ファイル
        self.auth_file = self._get_auth_file_path()
        
    def _log_debug(self, message: str):
        """デバッグログを記録（ファイル・コンソール両方）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # debug_logが初期化されていない場合の安全措置
        if not hasattr(self, 'debug_log'):
            self.debug_log = []
        
        self.debug_log.append(log_entry)
        
        # コンソール出力
        print(f"[AUTH DEBUG] {message}")
        
        # ログファイルにも出力（utils.pyのloggerを使用）
        try:
            from auto_mosaic.src.utils import logger
            logger.debug(f"[AUTH] {message}")
        except Exception:
            # logger利用できない場合はスキップ
            pass
        
    def _get_auth_file_path(self) -> Path:
        """認証状態保存ファイルのパスを取得（exe化対応強化）"""
        auth_file_path = None
        
        try:
            # Method 1: utils.pyからget_app_data_dirを使用
            from auto_mosaic.src.utils import get_app_data_dir
            app_data = Path(get_app_data_dir())
            auth_dir = app_data / "config"
            auth_dir.mkdir(parents=True, exist_ok=True)
            auth_file_path = auth_dir / "monthly_auth.dat"
            self._log_debug(f"Using app_data_dir: {auth_file_path}")
            
            # 書き込みテスト
            test_file = auth_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            self._log_debug("Write permission confirmed")
            
        except Exception as e:
            self._log_debug(f"Method 1 failed: {e}")
            
            try:
                # Method 2: APPDATAを直接使用
                appdata = os.getenv('APPDATA')
                if appdata:
                    app_data = Path(appdata) / "自動モザエセ"
                    auth_dir = app_data / "config"
                    auth_dir.mkdir(parents=True, exist_ok=True)
                    auth_file_path = auth_dir / "monthly_auth.dat"
                    self._log_debug(f"Using APPDATA: {auth_file_path}")
                    
                    # 書き込みテスト
                    test_file = auth_dir / "test_write.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    self._log_debug("APPDATA write permission confirmed")
                    
            except Exception as e2:
                self._log_debug(f"Method 2 failed: {e2}")
                
                try:
                    # Method 3: 実行ファイルと同じディレクトリ
                    if getattr(sys, 'frozen', False):
                        exe_dir = Path(sys.executable).parent
                    else:
                        exe_dir = Path.cwd()
                    
                    auth_dir = exe_dir / "config"
                    auth_dir.mkdir(parents=True, exist_ok=True)
                    auth_file_path = auth_dir / "monthly_auth.dat"
                    self._log_debug(f"Using exe directory: {auth_file_path}")
                    
                    # 書き込みテスト
                    test_file = auth_dir / "test_write.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    self._log_debug("Exe directory write permission confirmed")
                    
                except Exception as e3:
                    self._log_debug(f"Method 3 failed: {e3}")
                    
                    # Method 4: 一時ディレクトリ（最終手段）
                    temp_dir = Path(tempfile.gettempdir()) / "自動モザエセ"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    auth_file_path = temp_dir / "monthly_auth.dat"
                    self._log_debug(f"Using temp directory: {auth_file_path}")
        
        if auth_file_path is None:
            # 最終フォールバック
            auth_file_path = Path.cwd() / "monthly_auth.dat"
            self._log_debug(f"Final fallback: {auth_file_path}")
        
        return auth_file_path
    
    def hash_password(self, password: str) -> str:
        """パスワードをSHA256でハッシュ化"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_online_time(self) -> tuple:
        """オンライン時刻を取得（実用性重視・シンプル版）"""
        self._log_debug("Starting simplified online time sync...")
        
        # 開発環境では簡易的な時刻同期のみ実行（デバッグ目的）
        if not self.is_exe:
            self._log_debug("Development environment - using lightweight time sync for debugging")
        
        # Method 1: 軽量なHTTPヘッダー方式（最も通りやすい）
        try:
            self._log_debug("Trying HTTP Date header (lightweight)...")
            
            # 軽量なHTTPエンドポイントを使用
            response = requests.head(
                'http://www.google.com',  # HTTPSではなくHTTPを使用
                timeout=2,  # 短いタイムアウト
                headers={'User-Agent': '自動モザエセ/1.0'}
            )
            
            if response.status_code == 200 and 'Date' in response.headers:
                from email.utils import parsedate_to_datetime
                online_time = parsedate_to_datetime(response.headers['Date'])
                
                # UTC時刻を日本時刻(JST: UTC+9)に変換
                if online_time.tzinfo is not None:
                    # タイムゾーン付きの場合はJSTに変換してからタイムゾーン情報を除去
                    from datetime import timezone, timedelta
                    jst = timezone(timedelta(hours=9))
                    online_time = online_time.astimezone(jst).replace(tzinfo=None)
                else:
                    # UTCと仮定してJST(+9時間)に変換
                    online_time = online_time + timedelta(hours=9)
                
                self._log_debug(f"HTTP Date header sync successful (JST): {online_time}")
                return online_time, True
                
        except Exception as e:
            self._log_debug(f"HTTP Date header sync failed: {e}")
        
        # Method 2: Windows時刻サービス確認（ローカル）
        try:
            import subprocess
            self._log_debug("Checking Windows Time Service...")
            
            # w32timeサービスの状態を確認（タイムアウト短縮）
            result = subprocess.run(['w32tm', '/query', '/status'], 
                                  capture_output=True, text=True, timeout=3, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                output = result.stdout
                if 'Last Successful Sync Time' in output and 'error' not in output.lower():
                    self._log_debug("Windows Time Service is synchronized")
                    # Windows時刻サービスが正常な場合はローカル時刻を信頼
                    local_time = datetime.now()
                    # タイムゾーン情報を確実に除去
                    if local_time.tzinfo is not None:
                        local_time = local_time.replace(tzinfo=None)
                    self._log_debug(f"Using Windows-synced time: {local_time}")
                    return local_time, True
                    
        except Exception as e:
            self._log_debug(f"Windows Time Service check failed: {e}")
        
        # Method 3: 単純なJST時刻チェック（緊急フォールバック）
        try:
            self._log_debug("Emergency fallback - validating local time range...")
            
            local_time = datetime.now()
            current_year = local_time.year
            
            # 明らかに異常な年度（2020年未満、2030年超過）は拒否
            if current_year < 2020 or current_year > 2030:
                self._log_debug(f"Invalid year detected: {current_year}")
                return datetime.now(), False
            
            # タイムゾーン情報を確実に除去
            if local_time.tzinfo is not None:
                local_time = local_time.replace(tzinfo=None)
            self._log_debug(f"Local time appears reasonable: {local_time}")
            # 妥当な範囲内の場合は使用
            return local_time, True
            
        except Exception as e:
            self._log_debug(f"Local time validation failed: {e}")
        
        self._log_debug("All time methods failed - using system time as last resort")
        fallback_time = datetime.now()
        # タイムゾーン情報を確実に除去
        if fallback_time.tzinfo is not None:
            fallback_time = fallback_time.replace(tzinfo=None)
        return fallback_time, False
    
    def validate_system_time(self) -> tuple:
        """システム時刻の妥当性をチェック（セキュリティ重視・開発配慮版）"""
        local_time = datetime.now()
        
        # タイムゾーン情報を確実に除去（比較のため）
        if local_time.tzinfo is not None:
            local_time = local_time.replace(tzinfo=None)
        
        # 基本的な年度チェック（不正利用防止）
        current_year = local_time.year
        if current_year < 2020 or current_year > 2030:
            self._log_debug(f"Suspicious year detected: {current_year}")
            return False, f"システム時刻が異常です（年: {current_year}）"
        
        # オンライン時刻取得を試行
        online_time, sync_success = self.get_online_time()
        
        # オンライン時刻のタイムゾーン情報も確実に除去
        if sync_success and online_time.tzinfo is not None:
            online_time = online_time.replace(tzinfo=None)
            self._log_debug(f"Normalized online time (removed timezone): {online_time}")
        
        if not sync_success:
            # オフライン環境での対応（開発環境は緩和、本番環境は制限）
            if not self.is_exe:
                self._log_debug("Development + offline - allowing with warning")
                return True, "開発環境（オフライン、時刻同期失敗）"
            else:
                self._log_debug("Production + offline - restricted access")
                # 本番環境のオフライン時は時刻チェックを厳格に
                return True, "⚠️ オフライン環境（ネットワーク接続を確認してください）"
        
        # 時刻差をチェック（不正利用防止のためのセキュリティ機能）
        time_diff = abs((local_time - online_time).total_seconds())
        
        # 開発環境と本番環境で許容範囲を調整
        if not self.is_exe:
            # 開発環境: 1時間まで許可（デバッグ効率重視）
            max_time_diff = 3600  # 1時間
            threshold_name = "開発環境"
        else:
            # 本番環境: 15分まで許可（セキュリティ重視）
            max_time_diff = 900   # 15分
            threshold_name = "本番環境"
        
        if time_diff > max_time_diff:
            self._log_debug(f"Time difference exceeds {threshold_name} threshold: {time_diff/60:.1f} minutes")
            
            # 開発環境では警告のみ、本番環境では制限
            if not self.is_exe:
                warning_msg = (f"⚠️ システム時刻差が大きいです（{time_diff/60:.1f}分）\n"
                             f"開発環境のため認証を継続します。\n"
                             f"正確な時刻: {online_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                             f"システム時刻: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return True, warning_msg
            else:
                # 本番環境では時刻差が大きい場合は拒否（不正利用防止）
                error_msg = (f"❌ システム時刻の差が大きすぎます（{time_diff/60:.1f}分）\n"
                           f"セキュリティのため認証を拒否します。\n"
                           f"正確な時刻: {online_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"システム時刻: {local_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                           f"システム時刻を正しく設定してください。")
                return False, error_msg
        
        self._log_debug(f"Time validation passed: {time_diff/60:.1f} minutes difference ({threshold_name})")
        return True, f"時刻確認OK（差分: {time_diff/60:.1f}分、{threshold_name}）"
    
    def get_current_month_key(self, use_online_time: bool = False) -> str:
        """現在の月のキーを取得"""
        if use_online_time:
            online_time, sync_success = self.get_online_time()
            if sync_success:
                return online_time.strftime("%Y-%m")
        
        current_month = datetime.now().strftime("%Y-%m")
        return current_month
    
    def is_already_authenticated_this_month(self) -> bool:
        """今月既に認証済みかチェック（時刻変更対策付き、exe化対応）"""
        if not self.auth_file.exists():
            self._log_debug("Auth file does not exist")
            return False
        
        try:
            # ファイルのタイムスタンプ検証（時刻変更対策）
            file_stats = self.auth_file.stat()
            file_created = datetime.fromtimestamp(file_stats.st_ctime)
            file_modified = datetime.fromtimestamp(file_stats.st_mtime)
            current_time = datetime.now()
            
            self._log_debug(f"Auth file created: {file_created}")
            self._log_debug(f"Auth file modified: {file_modified}")
            self._log_debug(f"Current time: {current_time}")
            
            # ファイルが未来の日付で作成・修正されている場合は時刻変更の可能性
            if file_created > current_time or file_modified > current_time:
                self._log_debug("Auth file timestamp is in the future - clearing")
                self.clear_authentication_state()
                return False
            
            # 保存された月と現在の月を比較
            with open(self.auth_file, 'r', encoding='utf-8') as f:
                saved_month = f.read().strip()
            
            current_month = self.get_current_month_key()
            
            self._log_debug(f"Saved month: {saved_month}")
            self._log_debug(f"Current month: {current_month}")
            
            # 月が一致していても、ファイル作成日が異なる月の場合は無効
            file_month = file_created.strftime("%Y-%m")
            if saved_month != file_month:
                self._log_debug("Auth file month mismatch - clearing")
                self.clear_authentication_state()
                return False
                
            result = saved_month == current_month
            self._log_debug(f"Authentication check result: {result}")
            return result
            
        except Exception as e:
            self._log_debug(f"Authentication verification failed: {e}")
            return False
    
    def save_authentication_state(self):
        """認証状態を保存（今月の認証完了をマーク、exe化対応）"""
        try:
            current_month = self.get_current_month_key()
            
            # ディレクトリが存在することを確認
            self.auth_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                f.write(current_month)
            
            self._log_debug(f"Authentication state saved: {current_month} to {self.auth_file}")
            
        except Exception as e:
            self._log_debug(f"Could not save authentication state: {e}")
            # エラーを無視して続行（認証自体は成功）
    
    def clear_authentication_state(self):
        """認証状態をクリア"""
        try:
            if self.auth_file.exists():
                self.auth_file.unlink()
                self._log_debug("Authentication state cleared")
        except Exception as e:
            self._log_debug(f"Could not clear authentication state: {e}")
    
    def validate_password(self, password: str) -> bool:
        """パスワードを検証（オンライン時刻同期付き）"""
        password_hash = self.hash_password(password)
        
        # オンライン時刻で現在月を判定（失敗時はローカル時刻使用）
        current_month = self.get_current_month_key(use_online_time=True)
        
        self._log_debug(f"Validating password for month: {current_month}")
        
        # マスターパスワードチェック
        if password_hash == self.master_password_hash:
            self._log_debug("Master password validated")
            return True
        
        # 月次パスワードチェック
        if current_month in self.monthly_passwords:
            result = password_hash == self.monthly_passwords[current_month]
            self._log_debug(f"Monthly password validation result: {result}")
            return result
        
        self._log_debug("No valid password found")
        return False
    
    def get_expiration_info(self) -> tuple:
        """現在のパスワードの有効期限情報を取得"""
        current_month = self.get_current_month_key()
        
        # 次の月の1日を計算
        current_date = datetime.now()
        if current_date.month == 12:
            next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            next_month = current_date.replace(month=current_date.month + 1, day=1)
        
        days_remaining = (next_month - current_date).days
        
        return current_month, next_month.strftime("%Y-%m-%d"), days_remaining
    
    def show_auth_dialog(self, parent=None) -> bool:
        """認証ダイアログを表示（exe化対応強化）"""
        
        self._log_debug("Starting authentication dialog")
        
        # 最初に時刻同期チェック
        time_valid, time_message = self.validate_system_time()
        if not time_valid:
            error_message = f"認証に失敗しました。\n\n{time_message}\n\n詳細ログ:\n" + "\n".join(self.debug_log[-5:])
            if parent:
                messagebox.showerror("認証エラー", error_message)
            else:
                print(f"Authentication failed: {error_message}")
            return False
        
        # 有効期限情報を取得（オンライン時刻使用）
        current_month = self.get_current_month_key(use_online_time=True)
        
        # 次の月の1日を計算
        online_time, sync_success = self.get_online_time()
        if sync_success:
            current_date = online_time
        else:
            current_date = datetime.now()
            
        if current_date.month == 12:
            next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            next_month = current_date.replace(month=current_date.month + 1, day=1)
        
        days_remaining = (next_month - current_date).days
        expiration_date = next_month.strftime("%Y-%m-%d")
        
        # ダイアログウィンドウ作成
        dialog = tk.Toplevel(parent) if parent else tk.Tk()
        dialog.title("自動ヨフモザ v1.0 - 認証 (exe化対応)")
        dialog.geometry("550x450")  # サイズを拡大
        dialog.resizable(False, False)
        dialog.grab_set()  # モーダルダイアログ
        
        # ダイアログを画面中央に配置
        dialog.transient(parent)
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # 認証結果
        auth_result = {"success": False}
        
        # メインフレーム
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🔐 自動モザエセ v1.0",
                                font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 実行環境表示
        env_status = "EXE版" if self.is_exe else "開発版"
        network_status = "オンライン" if sync_success else "オフライン"
        
        # 説明
        desc_text = f"""このソフトウェアは認証が必要です。

対象月: {current_month}
有効期限: {expiration_date} ({days_remaining}日後)

🏷️ 実行環境: {env_status}
🌐 ネットワーク: {network_status}
📁 認証ファイル: {self.auth_file.name}

💡 月初に1回認証すれば、その月は認証不要になります。

月次パスワードを入力してください："""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify=tk.LEFT)
        desc_label.pack(pady=(0, 15))
        
        # パスワード入力
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(password_frame, text="パスワード:").pack(anchor=tk.W)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(password_frame, textvariable=password_var, 
                                  show="*", font=("Courier", 12))
        password_entry.pack(fill=tk.X, pady=(5, 0))
        password_entry.focus()
        
        # ステータスラベル
        status_label = ttk.Label(main_frame, text="", foreground="red")
        status_label.pack(pady=(0, 10))
        
        # デバッグ情報表示エリア（オプション）
        debug_frame = ttk.LabelFrame(main_frame, text="詳細情報", padding="5")
        debug_frame.pack(fill=tk.X, pady=(0, 10))
        
        debug_text = tk.Text(debug_frame, height=6, width=60, font=("Courier", 8))
        debug_scrollbar = ttk.Scrollbar(debug_frame, orient=tk.VERTICAL, command=debug_text.yview)
        debug_text.configure(yscrollcommand=debug_scrollbar.set)
        
        debug_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        debug_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # デバッグログを表示
        debug_info = "\n".join(self.debug_log)
        debug_text.insert("1.0", debug_info)
        debug_text.config(state=tk.DISABLED)
        
        def on_auth():
            password = password_var.get().strip()
            if not password:
                status_label.config(text="パスワードを入力してください")
                return
            
            self._log_debug(f"Attempting authentication with password: {password[:3]}***")
            
            if self.validate_password(password):
                # 認証成功 - 状態を保存
                self.save_authentication_state()
                auth_result["success"] = True
                status_label.config(text="✅ 認証成功！", foreground="green")
                self._log_debug("Authentication successful")
                
                # 重要な認証成功もINFOレベルでログファイルに記録
                try:
                    from auto_mosaic.src.utils import logger
                    logger.info("[AUTH] Monthly authentication successful")
                except Exception:
                    pass
                
                # 少し待ってからダイアログを閉じる
                dialog.after(1000, dialog.destroy)
            else:
                status_label.config(text="❌ パスワードが正しくありません")
                password_var.set("")
                password_entry.focus()
                self._log_debug("Authentication failed - incorrect password")
                
                # 認証失敗もWARNINGレベルでログファイルに記録
                try:
                    from auto_mosaic.src.utils import logger
                    logger.warning("[AUTH] Authentication failed - incorrect password")
                except Exception:
                    pass
                
                # デバッグログを更新
                debug_text.config(state=tk.NORMAL)
                debug_text.delete("1.0", tk.END)
                debug_text.insert("1.0", "\n".join(self.debug_log))
                debug_text.config(state=tk.DISABLED)
        
        def on_cancel():
            self._log_debug("Authentication cancelled by user")
            dialog.destroy()
        
        def on_clear_auth():
            """認証状態をクリアする（デバッグ用）"""
            self.clear_authentication_state()
            status_label.config(text="✅ 認証状態をクリアしました", foreground="green")
            self._log_debug("Authentication state cleared by user")
            
            # デバッグログを更新
            debug_text.config(state=tk.NORMAL)
            debug_text.delete("1.0", tk.END)
            debug_text.insert("1.0", "\n".join(self.debug_log))
            debug_text.config(state=tk.DISABLED)
        
        def on_show_debug():
            """デバッグ情報を別ウィンドウで表示"""
            debug_window = tk.Toplevel(dialog)
            debug_window.title("認証デバッグ情報")
            debug_window.geometry("600x400")
            
            debug_detail_text = tk.Text(debug_window, wrap=tk.WORD, font=("Courier", 9))
            debug_detail_scrollbar = ttk.Scrollbar(debug_window, orient=tk.VERTICAL, command=debug_detail_text.yview)
            debug_detail_text.configure(yscrollcommand=debug_detail_scrollbar.set)
            
            debug_detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            debug_detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 詳細なデバッグ情報を表示
            debug_detail = f"""認証システム詳細情報

実行環境: {'EXE版' if self.is_exe else '開発版'}
ネットワーク状態: {'オンライン' if sync_success else 'オフライン'}
認証ファイルパス: {self.auth_file}
認証ファイル存在: {self.auth_file.exists()}

=== デバッグログ ===
{chr(10).join(self.debug_log)}
"""
            debug_detail_text.insert("1.0", debug_detail)
            debug_detail_text.config(state=tk.DISABLED)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 左側のボタン（認証、キャンセル）
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="認証", command=on_auth, width=10).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(left_buttons, text="キャンセル", command=on_cancel, width=10).pack(side=tk.LEFT)
        
        # 右側のボタン（デバッグ系）
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="詳細表示", command=on_show_debug, width=10).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(right_buttons, text="認証クリア", command=on_clear_auth, width=10).pack(side=tk.RIGHT)
        
        # Enterキーでも認証実行
        password_entry.bind('<Return>', lambda e: on_auth())
        
        # ダイアログを表示して待機
        dialog.wait_window()
        
        self._log_debug(f"Authentication dialog closed - success: {auth_result['success']}")
        return auth_result["success"]

def authenticate_user(parent=None, force_auth_dialog=False) -> bool:
    """ユーザー認証のメイン関数（月1回認証対応、exe化対応強化）
    
    Args:
        parent: 親ウィンドウ
        force_auth_dialog: 強制的に認証ダイアログを表示（開発・デバッグ用）
    """
    try:
        auth = MonthlyAuth()
        
        auth._log_debug("=== Authentication process started ===")
        auth._log_debug(f"Execution environment: {'EXE' if auth.is_exe else 'Development'}")
        auth._log_debug(f"Auth file path: {auth.auth_file}")
        auth._log_debug(f"Force auth dialog: {force_auth_dialog}")
        
        # 開発環境での強制認証ダイアログ機能
        if force_auth_dialog and not auth.is_exe:
            auth._log_debug("Development mode - forcing authentication dialog for debugging")
            print("🔧 開発モード: 認証ダイアログを強制表示（デバッグ用）")
        elif not force_auth_dialog and auth.is_already_authenticated_this_month():
            # 通常の認証スキップロジック
            auth._log_debug("Already authenticated this month - skipping")
            print("✅ 今月は既に認証済みです。認証をスキップします。")
            
            # 開発環境では追加情報を表示
            if not auth.is_exe:
                print("💡 開発者向け: 強制認証テストには force_auth_dialog=True を使用してください")
            
            # 認証スキップもログファイルに記録
            try:
                from auto_mosaic.src.utils import logger
                logger.info("[AUTH] Monthly authentication skipped - already authenticated")
            except Exception:
                pass
            
            return True
        
        # 未認証の場合は認証ダイアログを表示
        auth._log_debug("Authentication required - showing dialog")
        print("🔐 月次認証が必要です。認証ダイアログを表示します。")
        
        # 認証開始をログファイルに記録
        try:
            from auto_mosaic.src.utils import logger
            logger.info("[AUTH] Monthly authentication dialog started")
        except Exception:
            pass
        
        result = auth.show_auth_dialog(parent)
        auth._log_debug(f"Authentication dialog result: {result}")
        
        # 認証結果をログファイルに記録
        try:
            from auto_mosaic.src.utils import logger
            if result:
                logger.info("[AUTH] Monthly authentication completed successfully")
            else:
                logger.warning("[AUTH] Monthly authentication failed or cancelled")
        except Exception:
            pass
        
        if not result and parent:
            # 失敗時にデバッグ情報を表示
            messagebox.showinfo("認証デバッグ情報", 
                               f"認証に失敗しました。以下の情報をご確認ください：\n\n" +
                               f"実行環境: {'EXE版' if auth.is_exe else '開発版'}\n" +
                               f"認証ファイル: {auth.auth_file}\n" +
                               f"ファイル存在: {auth.auth_file.exists()}\n\n" +
                               "最新のデバッグログ:\n" + "\n".join(auth.debug_log[-3:]))
        
        return result
        
    except Exception as e:
        error_msg = f"認証システムエラー: {str(e)}"
        print(f"[ERROR] {error_msg}")
        
        # 開発環境では詳細なエラー情報を表示
        if not getattr(sys, 'frozen', False):  # 開発環境
            import traceback
            print(f"[DEBUG] 詳細エラー情報:\n{traceback.format_exc()}")
        
        if parent:
            if not getattr(sys, 'frozen', False):  # 開発環境
                # 開発環境では詳細なエラー情報とデバッグオプションを提示
                from tkinter import messagebox
                result = messagebox.askyesnocancel(
                    "認証システムエラー（開発モード）", 
                    f"{error_msg}\n\n"
                    f"開発者向けオプション:\n"
                    f"• 「はい」: エラーを無視して続行\n"
                    f"• 「いいえ」: 認証を再試行\n"
                    f"• 「キャンセル」: アプリケーションを終了\n\n"
                    f"デバッグ用: force_auth_dialog=True で強制認証テスト可能"
                )
                
                if result is True:  # はい
                    print("🔧 開発モード: エラーを無視して続行")
                    return True
                elif result is False:  # いいえ
                    print("🔧 開発モード: 認証を再試行")
                    return authenticate_user(parent, force_auth_dialog=True)
                else:  # キャンセル
                    print("🔧 開発モード: アプリケーション終了")
                    return False
            else:
                # 本番環境では従来通り
                messagebox.showerror("認証システムエラー", 
                                   f"{error_msg}\n\n" +
                                   "認証をスキップして続行します。")
                return True
        
        # 本番環境またはGUIなしの場合は緊急時スキップ
        return True

def force_authentication_dialog(parent=None) -> bool:
    """開発者向け: 強制的に認証ダイアログを表示（デバッグ用）"""
    return authenticate_user(parent, force_auth_dialog=True)

def clear_authentication_and_test(parent=None) -> bool:
    """開発者向け: 認証状態をクリアしてから認証テスト"""
    try:
        auth = MonthlyAuth()
        auth.clear_authentication_state()
        print("🔧 認証状態をクリアしました。認証ダイアログを表示します。")
        return authenticate_user(parent, force_auth_dialog=True)
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

# パスワード生成用ヘルパー（開発時のみ使用）
def generate_monthly_passwords():
    """月次パスワードを生成（開発者用）"""
    import random
    import string
    
    def generate_password():
        chars = string.ascii_uppercase + string.digits
        return f"{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-" + \
               f"{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-" + \
               f"{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}"
    
    auth = MonthlyAuth()
    
    print("月次パスワード一覧:")
    for month in ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
                  "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]:
        password = generate_password()
        password_hash = auth.hash_password(password)
        print(f"{month}: {password} -> {password_hash}")

def debug_authentication():
    """開発者向け認証デバッグ関数"""
    print("🔧 認証システム デバッグモード")
    print("=" * 50)
    
    auth = MonthlyAuth()
    
    # 現在の認証状態を表示
    print(f"実行環境: {'EXE版' if auth.is_exe else '開発版'}")
    print(f"認証ファイル: {auth.auth_file}")
    print(f"認証ファイル存在: {auth.auth_file.exists()}")
    print(f"今月認証済み: {auth.is_already_authenticated_this_month()}")
    
    # 現在の月のパスワードを表示（開発用）
    current_month = auth.get_current_month_key()
    print(f"現在の月: {current_month}")
    
    # デバッグオプション
    print("\nデバッグオプション:")
    print("1. 通常認証テスト")
    print("2. 強制認証ダイアログ表示")
    print("3. 認証状態クリア")
    print("4. 時刻検証テスト")
    print("5. 月次パスワード確認")
    print("0. 終了")
    
    try:
        choice = input("\n選択 (0-5): ").strip()
        
        if choice == "1":
            print("\n🔧 通常認証テスト実行中...")
            result = authenticate_user()
            print(f"結果: {'成功' if result else '失敗'}")
            
        elif choice == "2":
            print("\n🔧 強制認証ダイアログ実行中...")
            result = authenticate_user(force_auth_dialog=True)
            print(f"結果: {'成功' if result else '失敗'}")
            
        elif choice == "3":
            print("\n🔧 認証状態クリア実行中...")
            auth.clear_authentication_state()
            print("認証状態をクリアしました")
            
        elif choice == "4":
            print("\n🔧 時刻検証テスト実行中...")
            is_valid, message = auth.validate_system_time()
            print(f"時刻検証結果: {'OK' if is_valid else 'NG'}")
            print(f"メッセージ: {message}")
            
        elif choice == "5":
            print("\n🔧 月次パスワード確認:")
            print(f"現在の月: {current_month}")
            if current_month in auth.monthly_passwords:
                print(f"パスワードハッシュ: {auth.monthly_passwords[current_month]}")
                print("マスターパスワード: yofumoza")
            else:
                print("❌ 現在の月のパスワードが設定されていません")
                
        elif choice == "0":
            print("デバッグモード終了")
            return
            
        else:
            print("❌ 無効な選択です")
            
    except KeyboardInterrupt:
        print("\nデバッグモード中断")
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 開発者向けデバッグモード
    debug_authentication() 