"""
自動モザエセのメインGUIアプリケーション
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from pathlib import Path
from typing import List, Optional, Dict
import cv2
import time
import numpy as np

from auto_mosaic.src.utils import logger, ProcessingConfig, validate_image_path, get_output_path, get_custom_output_path, calculate_tile_size, expand_masks_radial, is_first_run, mark_first_run_complete, create_desktop_shortcut, open_models_folder, get_models_dir, get_app_data_dir, expand_bboxes_individual, BBoxWithClass, get_device_info
from auto_mosaic.src.detector import create_detector
from auto_mosaic.src.segmenter import create_segmenter
from auto_mosaic.src.mosaic import create_mosaic_processor
from auto_mosaic.src.downloader import downloader
from auto_mosaic.src.detector import GenitalDetector
from auto_mosaic.src.segmenter import GenitalSegmenter
from auto_mosaic.src.mosaic import MosaicProcessor
from auto_mosaic.src.detector import MultiModelDetector
from auto_mosaic.src.auth import authenticate_user

class FirstRunSetupDialog:
    """初回起動時のセットアップダイアログ"""
    
    def __init__(self, parent):
        logger.info("FirstRunSetupDialog: Initializing setup dialog")
        print("🔧 FirstRunSetupDialog: 初期化開始")
        
        self.parent = parent
        self.result = {"create_shortcut": False, "setup_complete": False}
        self.dialog = None
        
        try:
            self._create_dialog()
            logger.info("FirstRunSetupDialog: Dialog creation completed")
            print("✅ FirstRunSetupDialog: ダイアログ作成完了")
        except Exception as e:
            logger.error(f"FirstRunSetupDialog: Error during creation - {e}")
            print(f"❌ FirstRunSetupDialog: 作成エラー - {e}")
            raise
    
    def _create_dialog(self):
        """セットアップダイアログを作成"""
        logger.info("FirstRunSetupDialog: Creating dialog window")
        print("📝 FirstRunSetupDialog: ダイアログウィンドウ作成中")
        
        try:
            self.dialog = tk.Toplevel(self.parent)
            logger.info("FirstRunSetupDialog: Toplevel window created")
            print("🪟 FirstRunSetupDialog: Toplevelウィンドウ作成完了")
            
            self.dialog.title("自動モザエセ v1.0 - 初回セットアップ")
            self.dialog.geometry("600x500")
            self.dialog.resizable(False, False)
            
            # モーダルダイアログ設定
            self.dialog.grab_set()
            logger.info("FirstRunSetupDialog: Modal dialog settings applied")
            print("🔒 FirstRunSetupDialog: モーダル設定完了")
            
            # ダイアログを画面中央に配置
            self.dialog.transient(self.parent)
            self.dialog.update_idletasks()
            
            # 画面中央計算
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            dialog_width = self.dialog.winfo_width()
            dialog_height = self.dialog.winfo_height()
            
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            
            self.dialog.geometry(f"+{x}+{y}")
            logger.info(f"FirstRunSetupDialog: Dialog positioned at ({x}, {y})")
            print(f"📍 FirstRunSetupDialog: ダイアログ位置設定 ({x}, {y})")
            
            # ダイアログを前面に表示
            self.dialog.lift()
            self.dialog.attributes('-topmost', True)
            self.dialog.focus_force()
            
            # 一時的にtopmostを解除
            self.dialog.after(200, lambda: self.dialog.attributes('-topmost', False))
            
            logger.info("FirstRunSetupDialog: Dialog brought to front")
            print("⬆️ FirstRunSetupDialog: ダイアログ前面表示完了")
            
            # GUI コンポーネントを作成
            self._create_dialog_components()
            
            logger.info("FirstRunSetupDialog: All components created successfully")
            print("🎨 FirstRunSetupDialog: 全コンポーネント作成完了")
            
        except Exception as e:
            logger.error(f"FirstRunSetupDialog: Error in _create_dialog - {e}")
            print(f"❌ FirstRunSetupDialog: _create_dialog エラー - {e}")
            raise
    
    def _create_dialog_components(self):
        """ダイアログのGUIコンポーネントを作成"""
        logger.info("FirstRunSetupDialog: Creating dialog components")
        print("🔨 FirstRunSetupDialog: GUIコンポーネント作成中")
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🎉 自動モザエセ v1.0 へようこそ！", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 説明テキスト
        desc_text = tk.Text(main_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        desc_content = """自動モザエセ v1.0 の初回セットアップを行います。

📁 データフォルダの作成
アプリケーションデータを以下の場所に保存します：
{app_data_dir}

このフォルダには以下が含まれます：
• models/ - モデルファイル格納場所
• logs/ - ログファイル
• config/ - 設定ファイル

📥 モデルファイルのダウンロードが必要です
セットアップ完了後、以下のモデルファイルをダウンロードして配置してください：

1. Anime NSFW Detection v4.0
   URL: https://civitai.com/models/1313556?modelVersionId=1863248
   ファイル: animeNSFWDetection_v40.zip
   クレジット: Anime NSFW Detection v4.0 by newtextdoc11996

2. SAM ViT-B
   URL: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
   ファイル: sam_vit_b_01ec64.pth

詳細な手順はREADME.mdをご参照ください。""".format(app_data_dir=get_app_data_dir())
        
        desc_text.config(state=tk.NORMAL)
        desc_text.insert("1.0", desc_content)
        desc_text.config(state=tk.DISABLED)
        
        # デスクトップショートカット
        self.shortcut_var = tk.BooleanVar(value=True)
        shortcut_frame = ttk.Frame(main_frame)
        shortcut_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(shortcut_frame, text="デスクトップにショートカットを作成", 
                       variable=self.shortcut_var).pack(anchor=tk.W)
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # スマートセットアップボタン（新機能）
        ttk.Button(button_frame, text="🤖 スマートセットアップ", 
                  command=self._smart_setup).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="modelsフォルダを開く", 
                  command=self._open_models_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="セットアップ完了", 
                  command=self._complete_setup).pack(side=tk.RIGHT)
        
        logger.info("FirstRunSetupDialog: Components created successfully")
        print("✅ FirstRunSetupDialog: コンポーネント作成完了")
    
    def show(self):
        """ダイアログを表示して結果を返す"""
        logger.info("FirstRunSetupDialog: Starting dialog display")
        print("👁️ FirstRunSetupDialog: ダイアログ表示開始")
        
        try:
            if self.dialog is None:
                logger.error("FirstRunSetupDialog: Dialog is None, cannot show")
                print("❌ FirstRunSetupDialog: ダイアログがNullです")
                return {"create_shortcut": False, "setup_complete": False}
            
            # 親ウィンドウを確実に表示状態にする
            if self.parent:
                self.parent.update()
                self.parent.deiconify()  # 親ウィンドウを表示状態に
            
            # ダイアログを確実に表示状態にする
            self.dialog.update_idletasks()
            self.dialog.update()
            self.dialog.deiconify()  # ダイアログを表示状態に
            
            # ダイアログを前面に強制表示
            self.dialog.lift()
            self.dialog.attributes('-topmost', True)
            self.dialog.focus_force()
            
            # 短時間後にtopmostを解除
            self.dialog.after(500, lambda: self.dialog.attributes('-topmost', False))
            
            if self.dialog.winfo_exists():
                logger.info("FirstRunSetupDialog: Dialog exists and is ready")
                print("✅ FirstRunSetupDialog: ダイアログ存在確認済み")
            else:
                logger.warning("FirstRunSetupDialog: Dialog does not exist")
                print("⚠️ FirstRunSetupDialog: ダイアログが存在しません")
            
            # ダイアログの待機開始
            logger.info("FirstRunSetupDialog: Waiting for user interaction")
            print("⏳ FirstRunSetupDialog: ユーザー操作待機中")
            
            # wait_window()を使用してダイアログが閉じられるまで待機
            self.dialog.wait_window()
            
            logger.info("FirstRunSetupDialog: Dialog closed, returning result")
            print("🔚 FirstRunSetupDialog: ダイアログが閉じられました")
            
            return self.result
            
        except Exception as e:
            logger.error(f"FirstRunSetupDialog: Error in show() - {e}")
            print(f"❌ FirstRunSetupDialog: show()エラー - {e}")
            return {"create_shortcut": False, "setup_complete": False}

    def _smart_setup(self):
        """スマートモデルセットアップを実行"""
        from tkinter import messagebox
        import threading
        import queue
        
        # CivitAI APIキー入力ダイアログ
        civitai_api_key = self._ask_civitai_api_key()
        
        # 確認ダイアログ
        if civitai_api_key:
            setup_message = (
                "スマートモデルセットアップを実行します。\n\n"
                "🔑 CivitAI APIキーが設定されました\n"
                "🤖 自動ダウンロード:\n"
                "・SAM ViT-B セグメンテーションモデル\n"
                "・YOLOv8m モデル\n"
                "・SAM ViT-H セグメンテーションモデル\n"
                "・Anime NSFW Detection v4.0 (CivitAI)\n\n"
                "実行しますか？"
            )
        else:
            setup_message = (
                "スマートモデルセットアップを実行します。\n\n"
                "🤖 自動ダウンロード:\n"
                "・SAM ViT-B セグメンテーションモデル\n"
                "・YOLOv8m モデル\n"
                "・SAM ViT-H セグメンテーションモデル\n\n"
                "🌐 ブラウザで開く:\n"
                "・Anime NSFW Detection v4.0 (CivitAI)\n\n"
                "実行しますか？"
            )
        
        result = messagebox.askyesno("スマートセットアップ", setup_message, icon='question')
        
        if not result:
            return
        
        # プログレスダイアログを作成
        progress_dialog = self._create_smart_setup_dialog()
        
        # スレッド間通信用のキュー
        progress_queue = queue.Queue()
        
        # キャンセルフラグ
        self.setup_cancelled = False
        
        def setup_thread():
            """バックグラウンドでセットアップを実行"""
            try:
                from auto_mosaic.src.downloader import downloader
                
                def progress_callback(action: str, model_name: str, current: int, total: int):
                    """プログレス更新コールバック（キューを使用）"""
                    try:
                        # キャンセルフラグをチェック
                        if self.setup_cancelled:
                            raise Exception("ユーザーによってキャンセルされました")
                        
                        progress_queue.put(("progress", action, model_name, current, total))
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                
                # ステータス更新
                progress_queue.put(("status", "セットアップを開始しています...", 0, 100))
                
                # CivitAI APIキーを設定
                if civitai_api_key:
                    downloader.set_civitai_api_key(civitai_api_key)
                
                # スマートセットアップを実行
                results = downloader.smart_model_setup(progress_callback)
                
                # 結果をキューに送信
                progress_queue.put(("complete", results))
                
            except Exception as e:
                logger.error(f"Smart setup error: {e}")
                progress_queue.put(("error", str(e)))
        
        def check_progress():
            """プログレスキューをチェックして UI を更新"""
            try:
                processed_messages = 0
                max_messages_per_cycle = 10  # 1サイクルあたりの最大メッセージ処理数
                
                while processed_messages < max_messages_per_cycle:
                    message = progress_queue.get_nowait()
                    message_type = message[0]
                    
                    if message_type == "progress":
                        _, action, model_name, current, total = message
                        self._update_smart_setup_progress(progress_dialog, action, model_name, current, total)
                    
                    elif message_type == "status":
                        _, status_text, current, total = message
                        self._update_smart_setup_status(progress_dialog, status_text, current, total)
                    
                    elif message_type == "complete":
                        results = message[1]
                        self._handle_smart_setup_results(progress_dialog, results)
                        return  # 完了時は monitoring を停止
                    
                    elif message_type == "error":
                        error_message = message[1]
                        self._handle_smart_setup_error(progress_dialog, error_message)
                        return  # エラー時も monitoring を停止
                    
                    processed_messages += 1
                        
            except queue.Empty:
                pass
            
            # より頻繁にチェック（50ms間隔）
            if progress_dialog.winfo_exists() and not self.setup_cancelled:
                progress_dialog.after(50, check_progress)
        
        # キャンセルボタン機能を追加
        def cancel_setup():
            self.setup_cancelled = True
            progress_dialog.destroy()
        
        # キャンセルボタンを接続
        progress_dialog.cancel_button.config(command=cancel_setup)
        
        # バックグラウンドスレッドでセットアップ開始
        setup_thread_obj = threading.Thread(target=setup_thread, daemon=True)
        setup_thread_obj.start()
        
        # プログレス監視開始
        progress_dialog.after(50, check_progress)
        
        # プログレスダイアログを表示（wait_windowを使用）
        progress_dialog.wait_window()

    def _ask_civitai_api_key(self):
        """CivitAI APIキーの入力を求める"""
        from tkinter import simpledialog
        
        dialog_text = (
            "CivitAI APIキーをお持ちですか？\n\n"
            "APIキーがある場合:\n"
            "• Anime NSFW Detection v4.0 を自動ダウンロード\n"
            "• より高速で確実なダウンロード\n\n"
            "APIキーがない場合:\n"
            "• ブラウザでCivitAIページを開きます\n"
            "• 手動でダウンロードしてください\n\n"
            "APIキーを入力してください (持っていない場合は空白のままOK):"
        )
        
        # カスタムダイアログを作成
        api_key_dialog = tk.Toplevel(self.dialog)
        api_key_dialog.title("CivitAI APIキー")
        api_key_dialog.geometry("450x300")
        api_key_dialog.resizable(False, False)
        api_key_dialog.transient(self.dialog)
        api_key_dialog.grab_set()
        
        # ダイアログを中央に配置
        api_key_dialog.geometry(f"+{self.dialog.winfo_x() + 50}+{self.dialog.winfo_y() + 50}")
        
        result = {"api_key": None}
        
        # メインフレーム
        main_frame = ttk.Frame(api_key_dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🔑 CivitAI APIキー設定", font=("", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 説明テキスト
        desc_text = tk.Text(main_frame, height=10, wrap=tk.WORD, font=("", 9))
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        desc_content = (
            "CivitAI APIキーをお持ちですか？\n\n"
            "【APIキーがある場合】\n"
            "✅ Anime NSFW Detection v4.0 を自動ダウンロード\n"
            "✅ より高速で確実なダウンロード\n"
            "✅ 手動操作が不要\n\n"
            "【APIキーがない場合】\n"
            "🌐 ブラウザでCivitAIページを開きます\n"
            "📥 手動でダウンロードしてください\n\n"
            "【APIキーの取得方法】\n"
            "1. CivitAI にログイン\n"
            "2. プロフィール → Account Settings → API Keys\n"
            "3. 「Add API Key」でキーを生成\n\n"
            "APIキーを入力してください (持っていない場合は空白のままOK):"
        )
        
        desc_text.insert("1.0", desc_content)
        desc_text.config(state=tk.DISABLED)
        
        # APIキー入力フィールド
        key_frame = ttk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(key_frame, text="APIキー:").pack(anchor=tk.W)
        api_key_entry = ttk.Entry(key_frame, width=50)  # show="*"を削除
        api_key_entry.pack(fill=tk.X, pady=(5, 0))
        
        # 右クリックメニューを追加
        def show_context_menu(event):
            """右クリック時にコンテキストメニューを表示"""
            # メニューを毎回新しく作成
            context_menu = tk.Menu(api_key_dialog, tearoff=0)
            
            def paste_text():
                """クリップボードからテキストをペースト"""
                try:
                    clipboard_text = api_key_entry.clipboard_get()
                    # 現在の選択範囲を削除してペースト
                    if api_key_entry.selection_present():
                        api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    api_key_entry.insert(tk.INSERT, clipboard_text)
                except tk.TclError:
                    # クリップボードが空の場合
                    pass
            
            def copy_text():
                """選択されたテキストをクリップボードにコピー"""
                try:
                    if api_key_entry.selection_present():
                        selected_text = api_key_entry.selection_get()
                        api_key_entry.clipboard_clear()
                        api_key_entry.clipboard_append(selected_text)
                except tk.TclError:
                    pass
            
            def cut_text():
                """選択されたテキストを切り取り"""
                try:
                    if api_key_entry.selection_present():
                        selected_text = api_key_entry.selection_get()
                        api_key_entry.clipboard_clear()
                        api_key_entry.clipboard_append(selected_text)
                        api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
            
            def select_all():
                """全てのテキストを選択"""
                api_key_entry.select_range(0, tk.END)
                api_key_entry.icursor(tk.END)
            
            # メニュー項目を追加
            context_menu.add_command(label="切り取り", command=cut_text)
            context_menu.add_command(label="コピー", command=copy_text)
            context_menu.add_command(label="貼り付け", command=paste_text)
            context_menu.add_separator()
            context_menu.add_command(label="すべて選択", command=select_all)
            
            # メニューを表示
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception as e:
                print(f"Context menu error: {e}")
            finally:
                # メニューを解放
                context_menu.grab_release()
        
        # 右クリックイベントをバインド
        api_key_entry.bind("<Button-3>", show_context_menu)
        
        # Ctrl+Vでのペースト機能も追加
        def handle_paste(event):
            """Ctrl+Vでのペースト処理"""
            try:
                clipboard_text = api_key_entry.clipboard_get()
                if api_key_entry.selection_present():
                    api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                api_key_entry.insert(tk.INSERT, clipboard_text)
                return "break"  # デフォルトのペースト処理を無効化
            except tk.TclError:
                return "break"
        
        api_key_entry.bind("<Control-v>", handle_paste)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            result["api_key"] = api_key_entry.get().strip() or None
            api_key_dialog.destroy()
        
        def on_cancel():
            result["api_key"] = None
            api_key_dialog.destroy()
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="スキップ", command=on_cancel).pack(side=tk.LEFT)
        
        # エンターキーでOK
        api_key_entry.bind('<Return>', lambda e: on_ok())
        api_key_entry.focus()
        
        # ダイアログを表示
        api_key_dialog.wait_window()
        
        return result["api_key"]

    def _create_smart_setup_dialog(self):
        """スマートセットアップ用のプログレスダイアログを作成"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("スマートモデルセットアップ")
        dialog.geometry("450x300")  # 高さを少し増加
        dialog.resizable(False, False)
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # ダイアログを中央に配置
        dialog.geometry(f"+{self.dialog.winfo_x() + 50}+{self.dialog.winfo_y() + 50}")
        
        # メインフレーム
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🤖 スマートモデルセットアップ", font=("", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 現在の作業表示
        current_label = ttk.Label(main_frame, text="初期化中...", font=("", 10))
        current_label.pack(anchor=tk.W, pady=(0, 5))
        
        # プログレスバー（determinate mode に変更）
        progress_bar = ttk.Progressbar(main_frame, mode='determinate', maximum=100)
        progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # パーセンテージ表示
        percent_label = ttk.Label(main_frame, text="0%", font=("", 9))
        percent_label.pack(anchor=tk.W, pady=(0, 10))
        
        # ログエリア
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        log_text = tk.Text(log_frame, height=6, font=("Consolas", 8), wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
        log_text.config(yscrollcommand=log_scrollbar.set)
        
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # キャンセルボタン
        cancel_button = ttk.Button(main_frame, text="キャンセル")
        cancel_button.pack()
        
        # ダイアログに要素を保存
        dialog.current_label = current_label
        dialog.progress_bar = progress_bar
        dialog.percent_label = percent_label
        dialog.log_text = log_text
        dialog.cancel_button = cancel_button
        
        return dialog

    def _update_smart_setup_progress(self, dialog, action: str, model_name: str, current: int, total: int):
        """スマートセットアップ進捗を更新"""
        if not dialog.winfo_exists():
            return
        
        action_texts = {
            "downloading": f"📥 ダウンロード開始: {model_name}",
            "download_progress": f"📥 ダウンロード中: {model_name}",
            "download_complete": f"✅ 完了: {model_name}",
            "download_failed": f"❌ 失敗: {model_name}",
            "opening_browser": f"🌐 ブラウザで開いています: {model_name}",
            "browser_opened": f"✅ ブラウザで開きました: {model_name}",
            "browser_failed": f"❌ ブラウザ起動失敗: {model_name}",
            "extracting": f"📦 展開中: {model_name}",
        }
        
        current_text = action_texts.get(action, f"処理中: {model_name}")
        dialog.current_label.config(text=current_text)
        
        # プログレスバーの更新
        if total > 0:
            if action in ["download_complete", "download_failed"]:
                # ダウンロード完了時は100%表示
                dialog.progress_bar['value'] = 100
                dialog.percent_label.config(text="100%")
            elif action == "download_progress":
                # ダウンロード中は実際の進捗を表示
                percent = int((current / total) * 100)
                dialog.progress_bar['value'] = percent
                dialog.percent_label.config(text=f"{percent}%")
                
                # ダウンロードサイズの表示
                if total > 1024:
                    current_mb = current / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    size_text = f" ({current_mb:.1f}/{total_mb:.1f} MB)"
                    dialog.current_label.config(text=current_text + size_text)
            else:
                # その他の場合は通常の計算
                percent = int((current / total) * 100)
                dialog.progress_bar['value'] = percent
                dialog.percent_label.config(text=f"{percent}%")
        
        # ログの1行更新機能
        timestamp = time.strftime("%H:%M:%S")
        
        if action == "download_progress":
            # ダウンロード進捗は1行で更新
            percent = int((current / total) * 100) if total > 0 else 0
            if total > 1024:
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                log_message = f"[{timestamp}] [download_progress] {model_name} - {percent}% ({current_mb:.1f}/{total_mb:.1f} MB)"
            else:
                log_message = f"[{timestamp}] [download_progress] {model_name} - {percent}%"
            
            # 最後の行が同じモデルのダウンロード進捗なら更新、そうでなければ新規追加
            if hasattr(dialog, '_last_progress_model') and dialog._last_progress_model == model_name:
                # 最後の行を削除して新しい進捗で更新
                dialog.log_text.delete("end-2l", "end-1l")
                dialog.log_text.insert(tk.END, log_message + "\n")
            else:
                # 新しいモデルの場合は新規追加
                dialog.log_text.insert(tk.END, log_message + "\n")
                dialog._last_progress_model = model_name
        else:
            # その他のアクションは通常通り追加
            log_message = f"[{timestamp}] [{action}] {model_name}"
            dialog.log_text.insert(tk.END, log_message + "\n")
            
            # ダウンロード完了時は進捗追跡をリセット
            if action in ["download_complete", "download_failed"]:
                dialog._last_progress_model = None
        
        dialog.log_text.see(tk.END)
        
        # UIを強制更新
        dialog.update_idletasks()
        
        # 次のモデルに移行する際はプログレスバーをリセット
        if action in ["download_complete", "download_failed"]:
            # 少し待ってからプログレスバーをリセット
            dialog.after(1000, lambda: self._reset_progress_for_next_model(dialog))

    def _reset_progress_for_next_model(self, dialog):
        """次のモデルのためにプログレスバーをリセット"""
        if dialog.winfo_exists():
            dialog.progress_bar['value'] = 0
            dialog.percent_label.config(text="0%")

    def _update_smart_setup_status(self, dialog, status_text: str, current: int, total: int):
        """スマートセットアップのステータスを更新"""
        if not dialog.winfo_exists():
            return
        
        dialog.current_label.config(text=status_text)
        
        if total > 0:
            percent = int((current / total) * 100)
            dialog.progress_bar['value'] = percent
            dialog.percent_label.config(text=f"{percent}%")
        
        # ログに追加
        timestamp = time.strftime("%H:%M:%S")
        dialog.log_text.insert(tk.END, f"[{timestamp}] [STATUS] {status_text}\n")
        dialog.log_text.see(tk.END)
        
        # UIを強制更新
        dialog.update_idletasks()

    def _handle_smart_setup_results(self, dialog, results: Dict):
        """スマートセットアップ結果を処理"""
        from tkinter import messagebox
        
        if not dialog.winfo_exists():
            return
        
        dialog.destroy()
        
        # 結果のサマリーを表示
        summary_lines = []
        
        if results["downloaded"]:
            summary_lines.append(f"✅ 自動ダウンロード完了: {len(results['downloaded'])}個")
        
        if results["opened_in_browser"]:
            summary_lines.append(f"🌐 ブラウザで開きました: {len(results['opened_in_browser'])}個")
        
        if results["failed"]:
            summary_lines.append(f"❌ 失敗: {len(results['failed'])}個")
        
        summary_text = "\n".join(summary_lines) if summary_lines else "すべてのモデルが既に利用可能です。"
        
        if results["opened_in_browser"]:
            messagebox.showinfo(
                "スマートセットアップ完了",
                f"セットアップが完了しました！\n\n"
                f"{summary_text}\n\n"
                "【重要】\n"
                "ブラウザで開いたページからAnime NSFW Detection v4.0を\n"
                "ダウンロードして配置してください。"
            )
        else:
            messagebox.showinfo(
                "スマートセットアップ完了",
                f"セットアップが完了しました！\n\n{summary_text}"
            )

    def _handle_smart_setup_error(self, dialog, error_message: str):
        """スマートセットアップエラーを処理"""
        from tkinter import messagebox
        
        if not dialog.winfo_exists():
            return
        
        dialog.destroy()
        
        messagebox.showerror(
            "セットアップエラー",
            f"スマートセットアップ中にエラーが発生しました：\n\n{error_message}"
        )
    
    def _open_models_folder(self):
        """modelsフォルダを開く"""
        try:
            open_models_folder()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("エラー", f"modelsフォルダを開けませんでした：{e}")
    
    def _complete_setup(self):
        """セットアップ完了処理"""
        # デスクトップショートカット作成
        if self.shortcut_var.get():
            success = create_desktop_shortcut()
            if success:
                logger.info("Desktop shortcut created successfully")
            else:
                logger.warning("Failed to create desktop shortcut")
        
        # 初回セットアップ完了をマーク
        mark_first_run_complete()
        
        self.result["create_shortcut"] = self.shortcut_var.get()
        self.result["setup_complete"] = True
        
        # ダイアログを閉じる
        self.dialog.destroy()
        
        # メインループは停止しない（修正）
        # アプリケーションは継続して動作する
        logger.info("First run setup completed - continuing to main application")

class AutoMosaicGUI:
    """自動モザエセのメインGUIアプリケーション"""
    
    def __init__(self):
        """Initialize GUI application"""
        self.root = tk.Tk()
        self.root.title("自動モザエセ v1.0 - 男女局部モザイク処理")
        
        # 🔐 認証チェック（最初に実行）
        logger.info("Starting authentication check...")
        if not authenticate_user(self.root):
            logger.warning("Authentication failed - exiting application")
            messagebox.showwarning("認証失敗", 
                                 "認証が失敗しました。\n" +
                                 "正しい月次パスワードを入力してください。\n\n" +
                                 "アプリケーションを終了します。")
            self.root.destroy()
            return
        
        logger.info("Authentication successful - proceeding with application startup")
        
        # 画面サイズを取得して適切なウィンドウサイズを設定
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 安全率1.2を考慮したウィンドウサイズ（画面の80%程度を使用）
        window_width = min(1200, int(screen_width * 0.8))
        window_height = min(900, int(screen_height * 0.8))
        
        # ウィンドウを画面中央に配置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # 最小サイズを設定（コンポーネントが隠れないように）
        self.root.minsize(800, 700)
        
        logger.info(f"Screen size: {screen_width}x{screen_height}, Window size: {window_width}x{window_height}")
        
        # Processing components (initialized on first use)
        self.detector = None
        self.segmenter = None
        self.mosaic_processor = None
        
        # GUI state
        self.image_paths = []
        self.output_dir = None  # 出力フォルダ
        self.processing = False
        self.progress_queue = queue.Queue()
        
        # Configuration
        self.config = ProcessingConfig()
        
        # GUIコンポーネントを先に作成（これによりメインウィンドウに中身が表示される）
        self._setup_gui()
        self._setup_progress_monitoring()
        
        # ウィンドウを前面に表示
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))  # 0.5秒後にtopmost解除
        
        # 初回起動チェック（GUIが作成された後に実行）
        if is_first_run():
            # メインウィンドウは隠さず、ダイアログをモーダルで表示
            setup_dialog = FirstRunSetupDialog(self.root)
            setup_result = setup_dialog.show()
            
            if setup_result["setup_complete"]:
                logger.info("First run setup completed successfully")
            else:
                logger.warning("First run setup was cancelled")
        
        logger.info("自動モザエセ GUI ready")
    
    def _setup_gui(self):
        """Setup GUI components"""
        # メニューバーを作成
        self._create_menu_bar()
        
        # スクロール可能なキャンバスを作成
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # パッキング
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main frame (スクロール可能フレーム内に配置)
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)  # 左列
        main_frame.columnconfigure(1, weight=1)  # 右列
        
        # マウスホイールでスクロール
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Title
        title_label = ttk.Label(main_frame, text="自動モザエセ v1.0",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 左列：ファイル選択と処理設定
        left_column = ttk.Frame(main_frame)
        left_column.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_column.columnconfigure(0, weight=1)
        
        # 右列：設定項目
        right_column = ttk.Frame(main_frame)
        right_column.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_column.columnconfigure(0, weight=1)
        
        # Configuration sections (右列)
        self._setup_basic_settings(right_column, row=0)
        self._setup_device_settings(right_column, row=1)
        self._setup_detector_settings(right_column, row=2)
        self._setup_mosaic_settings(right_column, row=3) 
        self._setup_model_settings(right_column, row=4)
        self._setup_mask_settings(right_column, row=5)
        self._setup_filename_settings(right_column, row=6)
        self._setup_output_settings(right_column, row=7)
        
        # File selection section (左列)
        self._setup_file_section(left_column, row=0)
        
        # Processing section (左列)
        self._setup_processing_section(left_column, row=1)
        
        # Progress section (左列)
        self._setup_progress_section(left_column, row=2)
        
        # Status section (左列)
        self._setup_status_section(left_column, row=3)
    
    def _create_menu_bar(self):
        """メニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="画像ファイルを追加...", command=self._add_images, accelerator="Ctrl+O")
        file_menu.add_command(label="フォルダを追加...", command=self._add_folder, accelerator="Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(label="出力フォルダを選択...", command=self._select_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit, accelerator="Ctrl+Q")
        
        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        
        # モデル管理サブメニュー
        model_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="モデル管理", menu=model_menu)
        model_menu.add_command(label="🤖 スマートセットアップ", command=self._menu_smart_setup)
        model_menu.add_command(label="📁 modelsフォルダを開く", command=open_models_folder)
        model_menu.add_separator()
        model_menu.add_command(label="🔄 初回セットアップダイアログ", command=self._menu_show_first_run_setup)
        
        # ツールメニュー
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        tools_menu.add_command(label="🔍 デバイス情報", command=self._show_device_info)
        tools_menu.add_command(label="📋 ログフォルダを開く", command=self._open_logs_folder)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="📖 使い方", command=self._show_help)
        help_menu.add_command(label="ℹ️ バージョン情報", command=self._show_about)
        
        # キーボードショートカット設定
        self.root.bind('<Control-o>', lambda e: self._add_images())
        self.root.bind('<Control-O>', lambda e: self._add_folder())
        self.root.bind('<Control-q>', lambda e: self.root.quit())

    def _menu_smart_setup(self):
        """メニューからスマートセットアップを実行"""
        self._run_smart_model_setup()

    def _menu_show_first_run_setup(self):
        """メニューから初回セットアップダイアログを表示"""
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "初回セットアップダイアログ",
            "初回セットアップダイアログを表示します。\n\n"
            "このダイアログでは以下の操作が可能です：\n"
            "• スマートモデルセットアップ\n"
            "• modelsフォルダを開く\n"
            "• デスクトップショートカット作成\n\n"
            "表示しますか？",
            icon='question'
        )
        
        if result:
            # 初回セットアップダイアログを表示
            self.root.withdraw()  # メインウィンドウを一時的に隠す
            setup_dialog = FirstRunSetupDialog(self.root)
            setup_result = setup_dialog.show()
            self.root.deiconify()  # メインウィンドウを再表示
            
            if setup_result["setup_complete"]:
                messagebox.showinfo("完了", "セットアップが完了しました。")

    def _show_device_info(self):
        """デバイス情報を表示"""
        from tkinter import messagebox
        from auto_mosaic.src.utils import get_recommended_device
        
        device_info = get_device_info()
        
        # 推奨デバイスを計算
        recommended = get_recommended_device("auto")
        
        # 利用可能デバイスのリストを作成
        available_devices = ["CPU"]
        if device_info.get('cuda_available', False):
            available_devices.append("GPU (CUDA)")
        
        # CUDAバージョン情報を取得
        cuda_version = device_info.get('debug_info', {}).get('torch_cuda_version', 'N/A')
        
        info_text = (
            f"🔍 デバイス情報\n\n"
            f"推奨デバイス: {recommended.upper()}\n"
            f"利用可能デバイス: {', '.join(available_devices)}\n"
            f"CUDA利用可能: {'Yes' if device_info.get('cuda_available', False) else 'No'}\n"
            f"GPU数: {device_info.get('gpu_count', 0)}\n"
            f"CUDAバージョン: {cuda_version}"
        )
        
        if device_info.get('gpu_names'):
            gpu_names = ', '.join(device_info['gpu_names'][:2])
            if len(device_info['gpu_names']) > 2:
                gpu_names += f" 他{len(device_info['gpu_names'])-2}個"
            info_text += f"\nGPU名: {gpu_names}"
        
        if device_info.get('memory_info'):
            memory_info = device_info['memory_info']
            info_text += f"\nGPUメモリ: {memory_info['free_gb']:.1f}GB空き / {memory_info['total_gb']:.1f}GB"
        
        messagebox.showinfo("デバイス情報", info_text)

    def _open_logs_folder(self):
        """ログフォルダを開く"""
        import subprocess
        import platform
        import os
        
        logs_dir = get_app_data_dir() / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        try:
            if platform.system() == "Windows":
                # Windowsの場合、最も確実な方法から試行
                try:
                    # 方法1: os.startfile を使用（Windows専用・最も確実）
                    os.startfile(str(logs_dir))
                    logger.info(f"Opened logs folder with os.startfile: {logs_dir}")
                except Exception:
                    try:
                        # 方法2: start コマンドを使用（shell=True）
                        subprocess.run(f'start "" "{logs_dir}"', check=True, shell=True)
                        logger.info(f"Opened logs folder with start command: {logs_dir}")
                    except subprocess.CalledProcessError:
                        # 方法3: explorer.exe を直接使用（最後の手段）
                        subprocess.run(["explorer.exe", str(logs_dir)], check=True, shell=False)
                        logger.info(f"Opened logs folder with explorer.exe: {logs_dir}")
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(logs_dir)], check=True)
                logger.info(f"Opened logs folder: {logs_dir}")
            else:  # Linux
                subprocess.run(["xdg-open", str(logs_dir)], check=True)
                logger.info(f"Opened logs folder: {logs_dir}")
        except Exception as e:
            from tkinter import messagebox
            logger.error(f"Failed to open logs folder: {str(e)}")
            messagebox.showerror("エラー", f"ログフォルダを開けませんでした：{e}")

    def _show_help(self):
        """ヘルプを表示"""
        import webbrowser
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "ヘルプ",
            "オンラインヘルプページを開きますか？\n\n"
            "• 使い方ガイド\n"
            "• FAQ\n"
            "• トラブルシューティング\n\n"
            "ブラウザでヘルプページを開きます。",
            icon='question'
        )
        
        if result:
            try:
                # GitHub READMEまたはドキュメントページを開く
                help_url = "https://github.com/your-repo/auto-mosaic#readme"
                webbrowser.open(help_url)
            except Exception as e:
                messagebox.showerror("エラー", f"ヘルプページを開けませんでした：{e}")

    def _show_about(self):
        """バージョン情報を表示"""
        from tkinter import messagebox
        
        about_text = (
            "🎨 自動ヨフモザ v1.0\n\n"
            "アニメ・イラスト画像の男女局部を\n"
            "自動検出してモザイク処理を適用するツール\n\n"
            "🔧 主要技術:\n"
            "• YOLO検出エンジン\n"
            "• SAMセグメンテーション\n"
            "• シームレスモザイク処理\n"
            "• FANZA基準対応\n\n"
            "📅 Version: 1.0.0\n"
            "🏢 Developed by: 自動モザエセ開発チーム\n"
            "📜 License: Proprietary"
        )
        
        messagebox.showinfo("バージョン情報", about_text)
    
    def _setup_file_section(self, parent, row):
        """Setup file selection section"""
        # Frame
        file_frame = ttk.LabelFrame(parent, text="📁 入力・出力設定", padding="15")
        file_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        # 入力画像リスト
        input_group = ttk.LabelFrame(file_frame, text="入力画像", padding="10")
        input_group.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_group.columnconfigure(0, weight=1)
        
        # File list
        list_frame = ttk.Frame(input_group)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(list_frame, height=6)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 入力操作ボタン
        input_btn_frame = ttk.Frame(input_group)
        input_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 追加ボタングループ
        add_frame = ttk.Frame(input_btn_frame)
        add_frame.pack(side=tk.LEFT)
        
        ttk.Button(add_frame, text="📷 画像追加", 
                  command=self._add_images, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(add_frame, text="📂 フォルダ追加", 
                  command=self._add_folder, width=15).pack(side=tk.LEFT)
        
        # クリアボタン（右寄せ）
        ttk.Button(input_btn_frame, text="🗑️ リストクリア", 
                  command=self._clear_images, width=15).pack(side=tk.RIGHT)
        
        # ファイル数表示
        self.file_count_label = ttk.Label(input_group, text="0 個の画像", font=("", 9))
        self.file_count_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        # 出力設定グループ
        output_group = ttk.LabelFrame(file_frame, text="出力設定", padding="10")
        output_group.grid(row=1, column=0, sticky=(tk.W, tk.E))
        output_group.columnconfigure(0, weight=1)
        
        # 出力フォルダ選択
        output_btn_frame = ttk.Frame(output_group)
        output_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(output_btn_frame, text="💾 出力フォルダ選択", 
                  command=self._select_output_folder, width=20).pack(side=tk.LEFT)
        
        # 出力フォルダ表示
        self.output_dir_label = ttk.Label(output_group, text="出力先: 元フォルダと同じ", 
                                         foreground="gray", font=("", 9))
        self.output_dir_label.grid(row=1, column=0, sticky=tk.W)
    
    def _setup_basic_settings(self, parent, row):
        """Setup basic processing settings"""
        config_frame = ttk.LabelFrame(parent, text="⚙️ 基本設定", padding="10")
        config_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Detection confidence setting
        ttk.Label(config_frame, text="検出信頼度:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.confidence_var = tk.DoubleVar(value=self.config.confidence)
        confidence_spin = ttk.Spinbox(config_frame, from_=0.0, to=1.0, increment=0.05,
                                     textvariable=self.confidence_var, width=10, format="%.2f")
        confidence_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(config_frame, text="(0.0=検出しやすい←→1.0=誤検出少ない | AI絵推奨:0.25)", foreground="gray").grid(row=0, column=2, sticky=tk.W)
        
        # Feather setting
        ttk.Label(config_frame, text="ぼかし:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.feather_var = tk.DoubleVar(value=self.config.feather / 10.0)  # 0-1範囲に正規化
        feather_spin = ttk.Spinbox(config_frame, from_=0.0, to=1.0, increment=0.1,
                                  textvariable=self.feather_var, width=10, format="%.1f")
        feather_spin.grid(row=1, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(config_frame, text="(境界の滑らかさ：0.0=シャープ、1.0=滑らか)", foreground="gray").grid(row=1, column=2, sticky=tk.W)
        
        # Range expansion setting
        ttk.Label(config_frame, text="範囲拡張:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.expansion_var = tk.IntVar(value=self.config.bbox_expansion)
        expansion_spin = ttk.Spinbox(config_frame, from_=-50, to=100, increment=5,
                                    textvariable=self.expansion_var, width=10)
        expansion_spin.grid(row=2, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(config_frame, text="px", foreground="gray").grid(row=2, column=2, sticky=tk.W)
        
        # 個別拡張範囲設定
        self.use_individual_expansion_var = tk.BooleanVar(value=self.config.use_individual_expansion)
        individual_check = ttk.Checkbutton(config_frame, text="個別拡張範囲", 
                                         variable=self.use_individual_expansion_var,
                                         command=self._on_individual_expansion_toggle)
        individual_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # 個別拡張範囲の詳細設定フレーム
        self.individual_frame = ttk.Frame(config_frame)
        self.individual_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        self.individual_frame.columnconfigure(0, weight=1)
        self.individual_frame.columnconfigure(1, weight=1)
        
        # 個別拡張範囲の各部位設定
        self.individual_expansion_vars = {}
        part_labels = {
            "penis": "男性器",
            "labia_minora": "小陰唇", 
            "labia_majora": "大陰唇",
            "testicles": "睾丸",
            "anus": "アナル",
            "nipples": "乳首",
            "x-ray": "透視",
            "cross-section": "断面",
            "all": "全て"
        }
        
        row = 0
        for part_key, part_label in part_labels.items():
            col = row % 2
            grid_row = row // 2
            
            part_frame = ttk.Frame(self.individual_frame)
            part_frame.grid(row=grid_row, column=col, sticky=(tk.W, tk.E), padx=(0, 10), pady=2)
            
            ttk.Label(part_frame, text=f"{part_label}:").pack(side=tk.LEFT, padx=(0, 5))
            var = tk.IntVar(value=self.config.individual_expansions[part_key])
            self.individual_expansion_vars[part_key] = var
            spinbox = ttk.Spinbox(part_frame, from_=-50, to=100, increment=5,
                                textvariable=var, width=6)
            spinbox.pack(side=tk.LEFT, padx=(0, 5))
            ttk.Label(part_frame, text="px").pack(side=tk.LEFT)
            
            row += 1
        
        # 初期状態設定
        self._on_individual_expansion_toggle()
        
    def _setup_device_settings(self, parent, row):
        """Setup device selection settings"""
        device_frame = ttk.LabelFrame(parent, text="🔧 デバイス設定", padding="10")
        device_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        device_frame.columnconfigure(0, weight=1)
        
        # GPU情報を取得
        self.device_info = get_device_info()
        
        # デバイス選択
        device_select_frame = ttk.Frame(device_frame)
        device_select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(device_select_frame, text="実行デバイス:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.device_var = tk.StringVar(value=self.config.device_mode)
        device_combo = ttk.Combobox(device_select_frame, textvariable=self.device_var, 
                                   state="readonly", width=12)
        
        # GPU利用可能性に応じて選択肢を設定
        if self.device_info["cuda_available"]:
            device_combo['values'] = ("auto", "cpu", "gpu")
            device_combo.set("auto")
        else:
            device_combo['values'] = ("cpu",)
            device_combo.set("cpu")
            
        device_combo.grid(row=0, column=1, sticky=tk.W)
        device_combo.bind('<<ComboboxSelected>>', self._on_device_change)
        
        # デバイス情報表示
        info_frame = ttk.Frame(device_frame)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # CPU情報
        cpu_info = "💻 CPU: 利用可能"
        ttk.Label(info_frame, text=cpu_info, foreground="green").grid(row=0, column=0, sticky=tk.W)
        
        # GPU情報
        if self.device_info["cuda_available"]:
            gpu_names = ", ".join(self.device_info["gpu_names"][:2])  # 最大2個まで表示
            if len(self.device_info["gpu_names"]) > 2:
                gpu_names += f" 他{len(self.device_info['gpu_names'])-2}個"
            
            gpu_info = f"🚀 GPU: {gpu_names}"
            ttk.Label(info_frame, text=gpu_info, foreground="green").grid(row=1, column=0, sticky=tk.W)
            
            # メモリ情報
            if self.device_info.get("memory_info"):
                memory_info = self.device_info["memory_info"]
                memory_text = f"   メモリ: {memory_info['free_gb']:.1f}GB空き / {memory_info['total_gb']:.1f}GB"
                color = "green" if memory_info['free_gb'] >= 2.0 else "orange"
                ttk.Label(info_frame, text=memory_text, foreground=color, font=("", 8)).grid(row=2, column=0, sticky=tk.W)
        else:
            gpu_info = "⚠️ GPU: 利用不可（CUDAが検出されませんでした）"
            ttk.Label(info_frame, text=gpu_info, foreground="red").grid(row=1, column=0, sticky=tk.W)
        
            # デバッグ情報の表示（exe化環境用）
            debug_info = self.device_info.get("debug_info", {})
            if debug_info.get("is_frozen"):
                # exe化環境での詳細情報
                debug_text = f"   exe実行環境: CUDA DLL検出数 {debug_info.get('cuda_dll_count', 0)}個"
                ttk.Label(info_frame, text=debug_text, foreground="orange", font=("", 8)).grid(row=2, column=0, sticky=tk.W)
                
                if debug_info.get("found_cuda_dlls"):
                    dll_list = ", ".join(debug_info["found_cuda_dlls"][:3])
                    if len(debug_info["found_cuda_dlls"]) > 3:
                        dll_list += f" 他{len(debug_info['found_cuda_dlls'])-3}個"
                    dll_text = f"   検出DLL: {dll_list}"
                    ttk.Label(info_frame, text=dll_text, foreground="gray", font=("", 7)).grid(row=3, column=0, sticky=tk.W)
        
        # 説明テキスト
        desc_frame = ttk.Frame(device_frame)
        desc_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        desc_text = """• auto: GPU利用可能なら自動選択（推奨）
• cpu: CPUのみ使用（安定動作、低速）
• gpu: GPU強制使用（高速、大メモリ消費）"""
        
        ttk.Label(desc_frame, text=desc_text, foreground="gray", font=("", 8), 
                 justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
    
    def _setup_detector_settings(self, parent, row):
        """Setup detector selection settings"""
        detector_frame = ttk.LabelFrame(parent, text="🔍 検出器設定", padding="10")
        detector_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        detector_frame.columnconfigure(0, weight=1)
        
        # 検出器モード選択
        mode_frame = ttk.Frame(detector_frame)
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(mode_frame, text="検出器モード:", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.detector_mode_var = tk.StringVar(value=self.config.detector_mode)
        
        # ラジオボタンで検出器選択
        detector_modes = [
            ("anime_only", "イラスト専用ロジックのみ", "イラスト専用ロジックのみ使用（アニメ・AI絵特化）"),
            ("nudenet_only", "実写専用ロジックのみ", "実写専用ロジックのみ使用（写真・実写対応）"),
            ("hybrid", "ハイブリッド（推奨）", "両方を併用して高精度検出（最も確実）")
        ]
        
        # NudeNetの利用可能性をチェック
        nudenet_status = self._check_nudenet_availability()
        nudenet_available = nudenet_status["available"]
        
        # NudeNetが利用できない場合は強制的にアニメ専用に変更
        if not nudenet_available and self.detector_mode_var.get() in ["nudenet_only", "hybrid"]:
            self.detector_mode_var.set("anime_only")
        
        self.detector_radio_buttons = {}
        for i, (mode, label, desc) in enumerate(detector_modes):
            # NudeNetが必要なモードは利用可能性に応じて制御
            if mode in ["nudenet_only", "hybrid"] and not nudenet_available:
                state = tk.DISABLED
                desc = f"{desc}（実写専用ロジック未対応）"
                label_color = "gray"
            else:
                state = tk.NORMAL
                label_color = "black"
            
            radio = ttk.Radiobutton(mode_frame, text=label, variable=self.detector_mode_var, 
                                  value=mode, command=self._on_detector_mode_change, state=state)
            radio.grid(row=i+1, column=0, sticky=tk.W, padx=(10, 0), pady=2)
            self.detector_radio_buttons[mode] = radio
            
            desc_label = ttk.Label(mode_frame, text=f"  {desc}", foreground="gray", font=("", 8))
            desc_label.grid(row=i+1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 詳細設定フレーム
        details_frame = ttk.Frame(detector_frame)
        details_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # イラスト専用ロジック設定
        anime_frame = ttk.LabelFrame(details_frame, text="イラスト専用ロジック設定", padding="5")
        anime_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.use_anime_var = tk.BooleanVar(value=self.config.use_anime_detector)
        anime_check = ttk.Checkbutton(anime_frame, text="使用する", variable=self.use_anime_var,
                                    command=self._on_detector_settings_change)
        anime_check.grid(row=0, column=0, sticky=tk.W)
        
        anime_desc = ttk.Label(anime_frame, text="アニメ・AI生成画像に特化した高精度検出", 
                              foreground="gray", font=("", 8))
        anime_desc.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # 実写専用ロジック設定
        nudenet_frame = ttk.LabelFrame(details_frame, text="実写専用ロジック設定", padding="5")
        nudenet_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.use_nudenet_var = tk.BooleanVar(value=self.config.use_nudenet)
        self.nudenet_check = ttk.Checkbutton(nudenet_frame, text="使用する", variable=self.use_nudenet_var,
                                           command=self._on_detector_settings_change)
        self.nudenet_check.grid(row=0, column=0, sticky=tk.W)
        
        # NudeNetが利用できない場合はチェックボックスを無効化
        logger.info("Checking NudeNet availability for GUI setup...")
        nudenet_status = self._check_nudenet_availability()
        logger.info(f"NudeNet availability result: {nudenet_status}")
        
        if not nudenet_status["available"]:
            logger.warning("NudeNet not available - disabling checkbox")
            self.use_nudenet_var.set(False)
            self.nudenet_check.config(state=tk.DISABLED)
        else:
            logger.info("NudeNet is available - enabling checkbox")
        
        nudenet_desc = ttk.Label(nudenet_frame, text="写真・実写・様々な画風に対応した汎用検出", 
                                foreground="gray", font=("", 8))
        nudenet_desc.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # NudeNetインストール状況チェック
        nudenet_status = self._check_nudenet_availability()
        if not nudenet_status["available"]:
            install_frame = ttk.Frame(nudenet_frame)
            install_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
            
            import sys
            if getattr(sys, 'frozen', False):
                # exe化時のメッセージ
                error_msg = nudenet_status.get("error", "unknown")
                if "import_error" in error_msg or "initialization_failed" in error_msg:
                    ttk.Label(install_frame, text="❌ 実写専用ロジックが利用できません（exe版制限）", 
                             foreground="red", font=("", 8)).grid(row=0, column=0, sticky=tk.W)
                    ttk.Label(install_frame, text="  イラスト専用ロジックをご利用ください", 
                             foreground="gray", font=("", 8)).grid(row=1, column=0, sticky=tk.W)
                else:
                    ttk.Label(install_frame, text="⚠️ 実写専用ロジックの初期化に失敗しました", 
                             foreground="orange", font=("", 8)).grid(row=0, column=0, sticky=tk.W)
            else:
                # 開発環境でのメッセージ
                ttk.Label(install_frame, text="⚠️ 実写専用ロジックが未インストールです", 
                         foreground="orange", font=("", 8)).grid(row=0, column=0, sticky=tk.W)
                
                install_btn = ttk.Button(install_frame, text="インストール", 
                                       command=self._install_nudenet, style="Small.TButton")
                install_btn.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # 初期設定を適用
        self._on_detector_mode_change()
    
    def _check_nudenet_availability(self) -> dict:
        """Check if NudeNet is available"""
        import sys
        
        logger.info(f"Checking NudeNet availability (frozen: {getattr(sys, 'frozen', False)})")
        
        # 統一されたテスト方法：直接NudeDetectorの初期化を試行
        try:
            # NudeNetモジュールのインポート
            import nudenet
            logger.info(f"NudeNet module imported, version: {getattr(nudenet, '__version__', 'unknown')}")
            
            # NudeDetectorクラスのインポート
            from nudenet import NudeDetector
            logger.info("NudeDetector class imported successfully")
            
            # 実際の初期化テスト
            logger.info("Attempting to initialize NudeDetector...")
            test_detector = NudeDetector()
            logger.info("NudeDetector initialized successfully")
            
            # 簡単な動作テスト
            try:
                from PIL import Image
                test_image = Image.new('RGB', (32, 32), color='white')
                result = test_detector.detect(test_image)
                logger.info(f"NudeNet detection test successful: {len(result)} detections")
            except Exception as test_e:
                logger.warning(f"NudeNet detection test failed, but initialization OK: {test_e}")
            
            # 成功
            version = getattr(nudenet, '__version__', 'exe_embedded' if getattr(sys, 'frozen', False) else 'unknown')
            logger.info("✅ NudeNet is fully available")
            return {"available": True, "version": version}
            
        except ImportError as e:
            logger.error(f"NudeNet import failed: {e}")
            return {"available": False, "error": f"import_error: {e}"}
        except Exception as e:
            logger.error(f"NudeNet initialization failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"available": False, "error": f"init_error: {e}"}
    
    def _install_nudenet(self):
        """Install NudeNet using pip"""
        import subprocess
        import sys
        import os
        
        try:
            # 実行ファイル環境かどうかを判定
            if getattr(sys, 'frozen', False):
                # 実行ファイル環境では直接インストールできない
                import tkinter.messagebox as msgbox
                msgbox.showwarning(
                    "インストール不可",
                    "実行ファイル版では直接インストールできません。\n\n"
                    "実写専用ロジックを使用するには：\n"
                    "1. Python環境で pip install nudenet を実行\n"
                    "2. Python版でビルドし直してください\n\n"
                    "または、イラスト専用ロジックのみをご利用ください。"
                )
                self._add_status_message("❌ 実行ファイル版では実写専用ロジックのインストールはできません", error=True)
                return
            
            # 開発環境でのインストール処理
            self._add_status_message("実写専用ロジックをインストール中...")
            
            # Install NudeNet
            result = subprocess.run([sys.executable, "-m", "pip", "install", "nudenet"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self._add_status_message("✅ 実写専用ロジックのインストールが完了しました")
                # Recreate detector settings to update UI
                self.setup_config_ui()
            else:
                self._add_status_message(f"❌ インストールに失敗しました: {result.stderr}", error=True)
                
        except Exception as e:
            self._add_status_message(f"❌ インストールエラー: {e}", error=True)
    
    def _on_detector_mode_change(self):
        """Handle detector mode change"""
        mode = self.detector_mode_var.get()
        self.config.detector_mode = mode
        
        # Update individual settings based on mode
        if mode == "anime_only":
            self.config.use_anime_detector = True
            self.config.use_nudenet = False
            self.use_anime_var.set(True)
            self.use_nudenet_var.set(False)
        elif mode == "nudenet_only":
            self.config.use_anime_detector = False
            self.config.use_nudenet = True
            self.use_anime_var.set(False)
            self.use_nudenet_var.set(True)
        elif mode == "hybrid":
            self.config.use_anime_detector = True
            self.config.use_nudenet = True
            self.use_anime_var.set(True)
            self.use_nudenet_var.set(True)
        
        # Update model checkboxes display based on new detector mode
        if hasattr(self, 'model_checkboxes'):
            self._update_model_checkboxes_display()
        
        logger.info(f"Detector mode changed to: {mode}")
    
    def _on_detector_settings_change(self):
        """Handle individual detector settings change"""
        # NudeNetの利用可能性をチェック
        nudenet_status = self._check_nudenet_availability()
        nudenet_available = nudenet_status["available"]
        
        self.config.use_anime_detector = self.use_anime_var.get()
        
        # NudeNetが利用できない場合は強制的にFalse
        if nudenet_available:
            self.config.use_nudenet = self.use_nudenet_var.get()
        else:
            self.config.use_nudenet = False
            self.use_nudenet_var.set(False)
        
        # Update mode if needed
        if self.config.use_anime_detector and self.config.use_nudenet:
            self.config.detector_mode = "hybrid"
            self.detector_mode_var.set("hybrid")
        elif self.config.use_anime_detector:
            self.config.detector_mode = "anime_only"
            self.detector_mode_var.set("anime_only")
        elif self.config.use_nudenet and nudenet_available:
            self.config.detector_mode = "nudenet_only"
            self.detector_mode_var.set("nudenet_only")
        else:
            # At least one must be selected - default to anime
            self.config.use_anime_detector = True
            self.use_anime_var.set(True)
            self.config.detector_mode = "anime_only"
            self.detector_mode_var.set("anime_only")
        
        logger.info(f"Detector settings updated: anime={self.config.use_anime_detector}, nudenet={self.config.use_nudenet}")
    
    def _on_device_change(self, event=None):
        """Handle device selection change"""
        self.config.device_mode = self.device_var.get()
        logger.info(f"Device mode changed to: {self.config.device_mode}")
        
    def _setup_mosaic_settings(self, parent, row):
        """Setup mosaic type and size settings"""
        mosaic_frame = ttk.LabelFrame(parent, text="🎨 処理オプション・粒度設定", padding="10")
        mosaic_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # モザイクタイプ複数選択
        type_frame = ttk.Frame(mosaic_frame)
        type_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(type_frame, text="処理オプション:", font=("", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # チェックボックス変数を初期化
        self.mosaic_type_vars = {
            "block": tk.BooleanVar(value=self.config.mosaic_types["block"]),
            "gaussian": tk.BooleanVar(value=self.config.mosaic_types["gaussian"]),
            "white": tk.BooleanVar(value=self.config.mosaic_types["white"]),
            "black": tk.BooleanVar(value=self.config.mosaic_types["black"])
        }
        
        # チェックボックス配置（2x2レイアウト）
        type_labels = {
            "block": "ブロックモザイク",
            "gaussian": "ガウスモザイク",
            "white": "白塗り",
            "black": "黒塗り"
        }
        
        row_pos = 1
        for i, (key, label) in enumerate(type_labels.items()):
            col_pos = i % 2
            if i > 0 and col_pos == 0:
                row_pos += 1
            
            checkbox = ttk.Checkbutton(type_frame, text=label, 
                                     variable=self.mosaic_type_vars[key],
                                     command=self._on_mosaic_type_change)
            checkbox.grid(row=row_pos, column=col_pos, sticky=tk.W, padx=(0, 20), pady=2)
        
        # FANZA対応状況の表示
        fanza_info_frame = ttk.Frame(mosaic_frame)
        fanza_info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.fanza_info_label = ttk.Label(fanza_info_frame, text="", foreground="gray", font=("", 8))
        self.fanza_info_label.pack(anchor=tk.W)
        
        # FANZA基準使用フラグ
        self.use_fanza_var = tk.BooleanVar(value=self.config.use_fanza_standard)
        self.fanza_check = ttk.Checkbutton(mosaic_frame, text="FANZA基準を使用（画像長辺の1%、最小4px）", 
                                          variable=self.use_fanza_var, command=self._on_fanza_toggle)
        self.fanza_check.grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        
        # 手動モザイクサイズ設定（タイプ別）
        manual_frame = ttk.Frame(mosaic_frame)
        manual_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # ブロックモザイク用設定
        block_frame = ttk.Frame(manual_frame)
        block_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.block_size_label = ttk.Label(block_frame, text="ブロックモザイク:")
        self.block_size_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.manual_tile_var = tk.IntVar(value=self.config.manual_tile_size)
        self.manual_tile_spin = ttk.Spinbox(block_frame, from_=4, to=64, increment=2,
                                           textvariable=self.manual_tile_var, width=8)
        self.manual_tile_spin.pack(side=tk.LEFT, padx=(0, 5))
        
        self.block_unit_label = ttk.Label(block_frame, text="px（FANZA基準を無効にした場合のみ有効）", foreground="gray")
        self.block_unit_label.pack(side=tk.LEFT)
        
        # ガウスモザイク用設定
        gaussian_frame = ttk.Frame(manual_frame)
        gaussian_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.gaussian_size_label = ttk.Label(gaussian_frame, text="ガウスモザイク:")
        self.gaussian_size_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.gaussian_blur_radius_var = tk.IntVar(value=getattr(self.config, 'gaussian_blur_radius', 8))
        self.gaussian_blur_spin = ttk.Spinbox(gaussian_frame, from_=2, to=32, increment=1,
                                             textvariable=self.gaussian_blur_radius_var, width=8)
        self.gaussian_blur_spin.pack(side=tk.LEFT, padx=(0, 5))
        
        self.gaussian_unit_label = ttk.Label(gaussian_frame, text="px（ぼかし半径、FANZA非対応）", foreground="gray")
        self.gaussian_unit_label.pack(side=tk.LEFT)
        
        # 初期状態の設定
        self._on_mosaic_type_change()
        self._on_fanza_toggle()
        
    def _setup_model_settings(self, parent, row):
        """Setup model selection settings"""
        self.model_frame = ttk.LabelFrame(parent, text="🎯 検出対象選択", padding="10")
        self.model_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.model_frame.columnconfigure(0, weight=1)
        self.model_frame.columnconfigure(1, weight=1)
        
        # 個別モデルファイルのチェックボックス変数
        self.model_penis_var = tk.BooleanVar(value=True)
        self.model_labia_minora_var = tk.BooleanVar(value=True)  # 小陰唇（anime_nsfw_v4）
        self.model_labia_majora_var = tk.BooleanVar(value=True)  # 大陰唇（nudenet）
        self.model_testicles_var = tk.BooleanVar(value=True)
        self.model_anus_var = tk.BooleanVar(value=True)
        self.model_nipples_var = tk.BooleanVar(value=False)
        self.model_xray_var = tk.BooleanVar(value=False)
        self.model_cross_section_var = tk.BooleanVar(value=False)
        self.model_all_var = tk.BooleanVar(value=False)
        
        # チェックボックスのリストを作成（動的表示制御用）
        self.model_checkboxes = {}
        
        # 全チェックボックスを作成（まだ配置しない）
        self._create_all_model_checkboxes()
        
        # 初期状態で検出器モードに基づく表示を設定
        self._update_model_checkboxes_display()
    
    def _create_all_model_checkboxes(self):
        """Create all model checkboxes but don't place them yet"""
        # 各チェックボックスを作成（まだgridしない）
        self.model_checkboxes["penis"] = ttk.Checkbutton(self.model_frame, text="男性器", variable=self.model_penis_var)
        self.model_checkboxes["labia_minora"] = ttk.Checkbutton(self.model_frame, text="小陰唇", variable=self.model_labia_minora_var)
        self.model_checkboxes["labia_majora"] = ttk.Checkbutton(self.model_frame, text="大陰唇", variable=self.model_labia_majora_var)
        self.model_checkboxes["testicles"] = ttk.Checkbutton(self.model_frame, text="睾丸", variable=self.model_testicles_var)
        self.model_checkboxes["anus"] = ttk.Checkbutton(self.model_frame, text="アナル", variable=self.model_anus_var)
        self.model_checkboxes["nipples"] = ttk.Checkbutton(self.model_frame, text="乳首", variable=self.model_nipples_var)
        self.model_checkboxes["xray"] = ttk.Checkbutton(self.model_frame, text="透視", variable=self.model_xray_var)
        self.model_checkboxes["cross_section"] = ttk.Checkbutton(self.model_frame, text="断面", variable=self.model_cross_section_var)
        self.model_checkboxes["all"] = ttk.Checkbutton(self.model_frame, text="全て", variable=self.model_all_var)
    
    def _update_model_checkboxes_display(self):
        """Update model checkboxes display based on detector mode"""
        # 既存のすべてのチェックボックスを非表示にする
        for checkbox in self.model_checkboxes.values():
            checkbox.grid_remove()
        
        detector_mode = self.detector_mode_var.get()
        
        # 検出器モードに応じて表示するチェックボックスを決定
        if detector_mode == "hybrid":
            # ハイブリッド：両方のモデルに対応（大陰唇は実写専用、小陰唇はイラスト専用）
            display_items = [
                ("penis", 0, 0), ("labia_minora", 0, 1),
                ("labia_majora", 1, 0), ("testicles", 1, 1),
                ("anus", 2, 0), ("nipples", 2, 1),
                ("xray", 3, 0), ("cross_section", 3, 1),
                ("all", 4, 0)
            ]
        elif detector_mode == "anime_only":
            # イラスト専用ロジック：小陰唇のみ
            display_items = [
                ("penis", 0, 0), ("labia_minora", 0, 1),
                ("testicles", 1, 0), ("anus", 1, 1),
                ("nipples", 2, 0), ("xray", 2, 1),
                ("cross_section", 3, 0), ("all", 3, 1)
            ]
            # 大陰唇チェックボックスを無効化
            if "labia_majora" in self.model_checkboxes:
                self.model_labia_majora_var.set(False)
        elif detector_mode == "nudenet_only":
            # 実写専用ロジック：大陰唇のみ
            display_items = [
                ("penis", 0, 0), ("labia_majora", 0, 1),
                ("testicles", 1, 0), ("anus", 1, 1),
                ("nipples", 2, 0)
            ]
            # 小陰唇とイラスト専用項目を無効化
            if "labia_minora" in self.model_checkboxes:
                self.model_labia_minora_var.set(False)
            self.model_xray_var.set(False)
            self.model_cross_section_var.set(False)
            self.model_all_var.set(False)
        else:
            # デフォルト：ハイブリッド
            display_items = [
                ("penis", 0, 0), ("labia_minora", 0, 1),
                ("labia_majora", 1, 0), ("testicles", 1, 1),
                ("anus", 2, 0), ("nipples", 2, 1),
                ("xray", 3, 0), ("cross_section", 3, 1),
                ("all", 4, 0)
            ]
        
        # 選択されたチェックボックスを配置
        for item_key, row, col in display_items:
            if item_key in self.model_checkboxes:
                self.model_checkboxes[item_key].grid(row=row, column=col, sticky=tk.W, pady=2)
        
    def _setup_mask_settings(self, parent, row):
        """Setup mask method settings"""
        mask_frame = ttk.LabelFrame(parent, text="🔲 マスク方式選択", padding="10")
        mask_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mask_frame.columnconfigure(0, weight=1)
        mask_frame.columnconfigure(1, weight=1)
        
        # マスク方式のチェックボックス
        self.sam_vit_b_var = tk.BooleanVar(value=True)
        self.sam_none_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(mask_frame, text="輪郭マスク（高精度・処理時間長）", variable=self.sam_vit_b_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(mask_frame, text="矩形マスク（処理時間短・精度低）", variable=self.sam_none_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 説明ラベル
        ttk.Label(mask_frame, text="高精度な結果が必要なら輪郭マスク、処理速度重視なら矩形マスクを選択", foreground="gray").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
    def _setup_filename_settings(self, parent, row):
        """Setup filename settings"""
        filename_frame = ttk.LabelFrame(parent, text="📝 ファイル名設定", padding="10")
        filename_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # ファイル名モード選択
        self.filename_mode_var = tk.StringVar(value=self.config.filename_mode)
        
        # ラジオボタン
        ttk.Radiobutton(filename_frame, text="そのまま（元ファイル名）", 
                       variable=self.filename_mode_var, value="original",
                       command=self._on_filename_mode_change).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(filename_frame, text="プレフィックス追加", 
                       variable=self.filename_mode_var, value="prefix",
                       command=self._on_filename_mode_change).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # プレフィックス設定
        prefix_frame = ttk.Frame(filename_frame)
        prefix_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(20, 0), pady=2)
        
        ttk.Label(prefix_frame, text="プレフィックス:").pack(side=tk.LEFT, padx=(0, 5))
        self.prefix_var = tk.StringVar(value=self.config.filename_prefix)
        self.prefix_entry = ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=15)
        self.prefix_entry.pack(side=tk.LEFT)
        # プレフィックス変更時の例示更新
        self.prefix_var.trace('w', lambda *args: self._update_filename_example())
        
        # 連番モード
        ttk.Radiobutton(filename_frame, text="連番リネーム", 
                       variable=self.filename_mode_var, value="sequential",
                       command=self._on_filename_mode_change).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 連番設定フレーム
        seq_frame = ttk.Frame(filename_frame)
        seq_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(20, 0), pady=2)
        
        ttk.Label(seq_frame, text="頭文字:").pack(side=tk.LEFT, padx=(0, 5))
        self.seq_prefix_var = tk.StringVar(value=self.config.sequential_prefix)
        self.seq_prefix_entry = ttk.Entry(seq_frame, textvariable=self.seq_prefix_var, width=8)
        self.seq_prefix_entry.pack(side=tk.LEFT, padx=(0, 10))
        # 連番プレフィックス変更時の例示更新
        self.seq_prefix_var.trace('w', lambda *args: self._update_filename_example())
        
        ttk.Label(seq_frame, text="開始番号:").pack(side=tk.LEFT, padx=(0, 5))
        self.seq_start_var = tk.StringVar(value=self.config.sequential_start_number)
        self.seq_start_entry = ttk.Entry(seq_frame, textvariable=self.seq_start_var, width=8)
        self.seq_start_entry.pack(side=tk.LEFT)
        # 開始番号変更時の例示更新
        self.seq_start_var.trace('w', lambda *args: self._update_filename_example())
        
        # 例示ラベル
        self.filename_example_label = ttk.Label(filename_frame, text="", foreground="gray")
        self.filename_example_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # 初期状態設定
        self._on_filename_mode_change()
        self._on_mosaic_type_change()  # 初期のモザイクタイプ状態を設定
    
    def _on_filename_mode_change(self):
        """Handle filename mode change"""
        mode = self.filename_mode_var.get()
        
        if mode == "original":
            self.prefix_entry.config(state=tk.DISABLED)
            self.seq_prefix_entry.config(state=tk.DISABLED)
            self.seq_start_entry.config(state=tk.DISABLED)
            
        elif mode == "prefix":
            self.prefix_entry.config(state=tk.NORMAL)
            self.seq_prefix_entry.config(state=tk.DISABLED)
            self.seq_start_entry.config(state=tk.DISABLED)
            
        elif mode == "sequential":
            self.prefix_entry.config(state=tk.DISABLED)
            self.seq_prefix_entry.config(state=tk.NORMAL)
            self.seq_start_entry.config(state=tk.NORMAL)
        
        # 例示を更新
        self._update_filename_example()
    
    def _setup_output_settings(self, parent, row):
        """Setup output settings"""
        output_frame = ttk.LabelFrame(parent, text="💾 出力オプション", padding="10")
        output_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 可視化オプション
        self.visual_var = tk.BooleanVar(value=self.config.visualize)
        visual_check = ttk.Checkbutton(output_frame, text="検出範囲を枠で表示した画像を保存", variable=self.visual_var)
        visual_check.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # シームレス処理は常にON（GUIに表示しない）
        self.seamless_var = tk.BooleanVar(value=True)
    
    def _setup_processing_section(self, parent, row):
        """Setup processing section"""
        # 処理セクションをLabelFrameで強調
        process_frame = ttk.LabelFrame(parent, text="🚀 処理実行", padding="15")
        process_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(10, 10))
        
        # ボタンフレーム
        btn_frame = ttk.Frame(process_frame)
        btn_frame.pack(fill=tk.X)
        
        # 大きな開始ボタン
        self.process_btn = ttk.Button(btn_frame, text="🎯 モザイク処理開始", 
                                     command=self._start_processing, 
                                     width=22)
        self.process_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 停止ボタン
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ 処理停止", 
                                  command=self._stop_processing, 
                                  state="disabled", width=15)
        self.stop_btn.pack(side=tk.LEFT)
    
    def _setup_progress_section(self, parent, row):
        """Setup progress section"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="待機中")
        self.progress_label.grid(row=0, column=1, sticky=tk.E)
    
    def _setup_status_section(self, parent, row):
        """Setup status section"""
        status_frame = ttk.LabelFrame(parent, text="📋 処理ログ", padding="5")
        status_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = tk.Text(status_frame, height=6, state=tk.DISABLED)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        status_scroll = ttk.Scrollbar(status_frame, orient="vertical")
        status_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.config(yscrollcommand=status_scroll.set)
        status_scroll.config(command=self.status_text.yview)
    
    def _setup_progress_monitoring(self):
        """Setup progress monitoring"""
        def check_queue():
            try:
                while True:
                    event_type, data = self.progress_queue.get_nowait()
                    
                    if event_type == "progress":
                        current, total = data
                        percent = (current / total * 100) if total > 0 else 0
                        self.progress_var.set(percent)
                        self.progress_label.config(text=f"{current}/{total}")
                    
                    elif event_type == "status":
                        self._add_status_message(data)
                    
                    elif event_type == "error":
                        self._add_status_message(f"エラー: {data}", error=True)
                        from tkinter import messagebox
                        messagebox.showerror("エラー", data)
                    
                    elif event_type == "done":
                        self._processing_complete()
                        
            except queue.Empty:
                pass
            
            # Schedule next check
            self.root.after(100, check_queue)
        
        # Start monitoring
        self.root.after(100, check_queue)
    
    def _add_images(self):
        """Add image files"""
        filetypes = [
            ("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
            ("すべてのファイル", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="画像ファイルを選択",
            filetypes=filetypes
        )
        
        added = 0
        for file_path in files:
            path = Path(file_path)
            if validate_image_path(path) and str(path) not in self.image_paths:
                self.image_paths.append(str(path))
                self.file_listbox.insert(tk.END, path.name)
                added += 1
        
        self._update_file_count()
        if added > 0:
            self._add_status_message(f"{added}個の画像を追加しました")
    
    def _add_folder(self):
        """Add images from folder"""
        folder_path = filedialog.askdirectory(title="画像フォルダを選択")
        if not folder_path:
            return
        
        folder = Path(folder_path)
        added = 0
        
        # サポートする画像形式（大文字小文字両対応）
        image_extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif', '*.webp',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.TIFF', '*.TIF', '*.WEBP'
        ]
        
        # フォルダ内を再帰的に検索
        for ext in image_extensions:
            for file_path in folder.rglob(ext):  # rglob で再帰検索
                if str(file_path) not in self.image_paths:
                    self.image_paths.append(str(file_path))
                    # 相対パスで表示（見やすくするため）
                    relative_path = file_path.relative_to(folder)
                    self.file_listbox.insert(tk.END, str(relative_path))
                    added += 1
        
        self._update_file_count()
        if added > 0:
            self._add_status_message(f"フォルダから{added}個の画像を追加しました（サブフォルダ含む）")
        else:
            self._add_status_message("フォルダ内に画像ファイルが見つかりませんでした")
    
    def _clear_images(self):
        """Clear image list"""
        self.image_paths.clear()
        self.file_listbox.delete(0, tk.END)
        self._update_file_count()
        self._add_status_message("画像リストをクリアしました")
    
    def _update_file_count(self):
        """Update file count label"""
        count = len(self.image_paths)
        self.file_count_label.config(text=f"{count} 個の画像")
    
    def _add_status_message(self, message: str, error: bool = False):
        """Add message to status text"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, full_message)
        
        if error:
            # Highlight error messages in red
            last_line = self.status_text.index(tk.END + "-2l")
            self.status_text.tag_add("error", last_line, tk.END + "-1c")
            self.status_text.tag_config("error", foreground="red")
        
        self.status_text.config(state=tk.DISABLED)
        self.status_text.see(tk.END)
    
    def _start_processing(self):
        """Start processing images"""
        if not self.image_paths:
            messagebox.showwarning("警告", "画像が選択されていません")
            return
        
        if self.processing:
            return
        
        # Update configuration
        self.config.confidence = self.confidence_var.get()  # 検出信頼度を更新
        self.config.feather = int(self.feather_var.get() * 10)  # 0-1を0-10にスケーリングして整数に
        self.config.bbox_expansion = self.expansion_var.get()
        self.config.visualize = self.visual_var.get()
        
        # デバイス設定を更新
        if hasattr(self, 'device_var'):
            self.config.device_mode = self.device_var.get()
        
        # 個別拡張範囲設定の更新
        self.config.use_individual_expansion = self.use_individual_expansion_var.get()
        for part_key, var in self.individual_expansion_vars.items():
            self.config.individual_expansions[part_key] = var.get()
        
        # ファイル名設定の更新
        self.config.filename_mode = self.filename_mode_var.get()
        self.config.filename_prefix = self.prefix_var.get()
        self.config.sequential_prefix = self.seq_prefix_var.get()
        self.config.sequential_start_number = self.seq_start_var.get()
        
        # 連番カウンターを初期化
        self.sequential_counter = 1
        
        # モザイク種類・粒度設定の更新（複数選択対応）
        for key, var in self.mosaic_type_vars.items():
            self.config.mosaic_types[key] = var.get()
        self.config.use_fanza_standard = self.use_fanza_var.get()
        self.config.manual_tile_size = self.manual_tile_var.get()
        self.config.gaussian_blur_radius = self.gaussian_blur_radius_var.get()
        
        # 選択されたモデルファイルの設定
        self.config.selected_models = {
            "penis": self.model_penis_var.get(),
            "labia_minora": self.model_labia_minora_var.get(),  # 小陰唇
            "labia_majora": self.model_labia_majora_var.get(),  # 大陰唇
            "testicles": self.model_testicles_var.get(),
            "anus": self.model_anus_var.get(),
            "nipples": self.model_nipples_var.get(),
            "x-ray": self.model_xray_var.get(),
            "cross-section": self.model_cross_section_var.get(),
            "all": self.model_all_var.get()
        }
        
        # SAMセグメンテーション選択の設定
        self.config.sam_use_vit_b = self.sam_vit_b_var.get()
        self.config.sam_use_none = self.sam_none_var.get()
        
        # どちらか一つは選択されている必要がある
        if not (self.config.sam_use_vit_b or self.config.sam_use_none):
            messagebox.showwarning("警告", "少なくとも1つのマスク方式を選択してください")
            return
        
        # 少なくとも1つのモデルが選択されているかチェック
        if not any(self.config.selected_models.values()):
            messagebox.showwarning("警告", "少なくとも1つのモデルファイルを選択してください")
            return
        
        # 出力フォルダ構造により上書きの心配なし（block/gaussian/white/blackサブフォルダに分離）
        
        # Start processing thread
        self.processing = True
        self.process_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        self._add_status_message("処理を開始します...")
        
        thread = threading.Thread(target=self._process_images, daemon=True)
        thread.start()
    
    def _stop_processing(self):
        """Stop processing"""
        self.processing = False
        self._add_status_message("処理を停止しています...")
    
    def _processing_complete(self):
        """Handle processing completion"""
        self.processing = False
        self.process_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_var.set(0)
        self.progress_label.config(text="完了")
        self._add_status_message("処理が完了しました")
    
    def _process_images(self):
        """Process images in background thread"""
        try:
            # Initialize components
            self.progress_queue.put(("status", "モデルを初期化しています..."))
            
            self._initialize_models()
            
            total_images = len(self.image_paths)
            
            for i, image_path in enumerate(self.image_paths):
                if not self.processing:
                    break
                
                try:
                    self._process_single_image(image_path, i + 1, total_images)
                except Exception as e:
                    error_msg = f"画像 {Path(image_path).name} の処理中にエラーが発生しました: {str(e)}"
                    self.progress_queue.put(("error", error_msg))
                    continue
            
            self.progress_queue.put(("done", None))
            
        except Exception as e:
            error_msg = f"処理中に重大なエラーが発生しました: {str(e)}"
            self.progress_queue.put(("error", error_msg))
            self.progress_queue.put(("done", None))
    
    def _process_single_image(self, image_path: str, current: int, total: int):
        """Process a single image"""
        import time
        
        path = Path(image_path)
        self.progress_queue.put(("status", f"処理中: {path.name}"))
        self.progress_queue.put(("progress", (current - 1, total)))
        
        start_time = time.time()
        
        # Load image
        load_start = time.time()
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"画像を読み込めませんでした: {path.name}")
        load_time = time.time() - load_start
        logger.info(f"[Image Load] Time: {load_time:.2f}s")
        
        # Detect genital regions
        detect_start = time.time()
        bboxes_with_class = self.detector.detect(image, self.config.confidence, config=self.config)
        detect_time = time.time() - detect_start
        logger.info(f"[Detection] Time: {detect_time:.2f}s")
        
        if not bboxes_with_class:
            # 検出されない場合は元画像をそのまま各モザイクタイプ別フォルダのNoMosaicサブフォルダに出力
            self.progress_queue.put(("status", f"{path.name}: No target regions detected - outputting original image to NoMosaic folders"))
            
            # 選択されたモザイクタイプ別フォルダのNoMosaicサブフォルダに元画像を出力
            selected_types = [key for key, value in self.config.mosaic_types.items() if value]
            
            for mosaic_type in selected_types:
                # モザイクタイプ別サブフォルダを作成（出力フォルダ指定がない場合は入力画像フォルダを使用）
                if self.output_dir:
                    type_output_dir = self.output_dir / mosaic_type
                else:
                    type_output_dir = path.parent / mosaic_type
                
                type_output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"[DEBUG] Created subfolder: {type_output_dir}")
                
                # NoMosaicサブフォルダを作成
                no_mosaic_dir = type_output_dir / "NoMosaic"
                no_mosaic_dir.mkdir(exist_ok=True)
                logger.info(f"[DEBUG] Created NoMosaic subfolder: {no_mosaic_dir}")
                
                original_output_path = get_custom_output_path(path, output_dir=no_mosaic_dir, 
                                                            suffix="", config=self.config, 
                                                            counter=self.sequential_counter)
                cv2.imwrite(str(original_output_path), image)
                logger.info(f"[No Detection - {mosaic_type}/NoMosaic] -> {original_output_path}")
            
            # 連番カウンターを更新（連番モードの場合）
            if self.config.filename_mode == "sequential":
                self.sequential_counter += 1
                
            total_time = time.time() - start_time
            logger.info(f"[No Detection - NoMosaic Output] Time: {total_time:.2f}s | Image: {path.name}")
            self.progress_queue.put(("status", f"{path.name}: No detection - saved original image to {len(selected_types)} NoMosaic folders - {total_time:.1f}s"))
            self.progress_queue.put(("progress", (current, total)))
            return
        
        # 個別拡張範囲処理を適用（矩形モードのみ）
        original_bboxes = [(x1, y1, x2, y2) for x1, y1, x2, y2, _, _ in bboxes_with_class]
        
        if self.config.sam_use_none:
            # 矩形モード: 矩形段階で拡張を適用
            if self.config.use_individual_expansion:
                # 個別拡張範囲を適用
                expanded_bboxes = expand_bboxes_individual(bboxes_with_class, self.config, image.shape[:2])
                logger.info(f"Applied individual expansion by class for rectangular mode (total: {len(expanded_bboxes)} regions)")
            else:
                # 通常拡張を適用
                from auto_mosaic.src.utils import expand_bboxes
                expanded_bboxes = expand_bboxes(original_bboxes, self.config.bbox_expansion, image.shape[:2])
                if self.config.bbox_expansion != 0:
                    logger.info(f"Applied bbox expansion {self.config.bbox_expansion:+d}px for rectangular mode")
        else:
            # 輪郭モード: 矩形段階では拡張しない（元の検出結果をそのまま使用）
            expanded_bboxes = original_bboxes
            logger.info(f"Using original bboxes for contour mode (expansion will be applied after segmentation)")

        # Generate masks and process separately for comparison
        mask_start = time.time()
        
        # Process each segmentation method separately for comparison
        sam_results = {}
        output_files = []
        
        if self.config.sam_use_vit_b:
            vit_b_start = time.time()
            # 輪郭モード: 元の検出結果を使用してSAM処理
            masks_b = self.segmenter_vit_b.masks(image, original_bboxes)
            vit_b_time = time.time() - vit_b_start
            sam_results["ViT-B"] = {"masks": len(masks_b), "time": vit_b_time}
            logger.info(f"  [SAM ViT-B] Time: {vit_b_time:.2f}s ({len(masks_b)} masks)")
            
            if masks_b:
                # ViT-B mosaic processing（SAM処理後に輪郭ベース拡張を適用）
                mosaic_b_start = time.time()
                
                # 輪郭モード用の設定を作成（拡張を有効化）
                contour_config = type('obj', (object,), {
                    'bbox_expansion': self.config.bbox_expansion,
                    'use_individual_expansion': self.config.use_individual_expansion,
                    'individual_expansions': getattr(self.config, 'individual_expansions', {}),
                    'use_fanza_standard': self.config.use_fanza_standard,
                    'manual_tile_size': self.config.manual_tile_size,
                    'mode': 'contour',  # 輪郭モードを指定
                    'bboxes_with_class': bboxes_with_class  # クラス情報を追加
                })()
                
                # 複数モザイクタイプ処理
                selected_types = [key for key, value in self.config.mosaic_types.items() if value]
                for mosaic_type in selected_types:
                    # モザイクタイプ別設定を作成
                    type_config = type('obj', (object,), {
                        'bbox_expansion': self.config.bbox_expansion,
                        'use_individual_expansion': self.config.use_individual_expansion,
                        'individual_expansions': getattr(self.config, 'individual_expansions', {}),
                        'use_fanza_standard': self.config.use_fanza_standard if mosaic_type == "block" else False,
                        'manual_tile_size': self.config.manual_tile_size,
                        'gaussian_blur_radius': self.config.gaussian_blur_radius,
                        'mode': 'contour',  # 輪郭モードを指定
                        'bboxes_with_class': bboxes_with_class  # クラス情報を追加
                    })()
                    
                    # シームレス処理（輪郭ベース拡張付き）
                    result_b = self.mosaic_processor.apply(
                        image, masks_b, 
                        feather=self.config.feather, 
                        strength=1.0,  # 強度は固定値1.0を使用
                        config=type_config,
                        mosaic_type=mosaic_type
                    )
                    
                    # モザイクタイプ別サブフォルダに保存（出力フォルダ指定がない場合は入力画像フォルダを使用）
                    if self.output_dir:
                        type_output_dir = self.output_dir / mosaic_type
                    else:
                        type_output_dir = path.parent / mosaic_type
                    
                    type_output_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[DEBUG] Created subfolder: {type_output_dir}")
                    
                    output_path_b = get_custom_output_path(path, output_dir=type_output_dir, 
                                                         suffix="", config=self.config, 
                                                         counter=self.sequential_counter)
                    cv2.imwrite(str(output_path_b), result_b)
                    output_files.append((f"輪郭マスク({mosaic_type})", output_path_b, len(masks_b)))
                    logger.info(f"  [輪郭マスク-{mosaic_type}] -> {output_path_b}")
                
                mosaic_b_time = time.time() - mosaic_b_start
                
                # 連番カウンターを更新（連番モードの場合）
                if self.config.filename_mode == "sequential":
                    self.sequential_counter += 1
        
        if self.config.sam_use_none:
            none_start = time.time()
            # Create simple rectangular masks from bounding boxes (no SAM segmentation)
            # 矩形モード: 拡張済みの矩形を使用
            bbox_masks = self._create_bbox_masks(image, expanded_bboxes)
            none_time = time.time() - none_start
            sam_results["None"] = {"masks": len(bbox_masks), "time": none_time}
            logger.info(f"  [BBox Only] Time: {none_time:.2f}s ({len(bbox_masks)} masks)")
            
            if bbox_masks:
                # 矩形マスク処理（拡張は既に適用済みなので追加拡張なし）
                mosaic_none_start = time.time()
                
                # 矩形モード用の設定を作成（拡張を無効化）
                rect_config = type('obj', (object,), {
                    'bbox_expansion': 0,  # 拡張は既に適用済み
                    'use_fanza_standard': self.config.use_fanza_standard,
                    'manual_tile_size': self.config.manual_tile_size,
                    'mode': 'rectangle'  # 矩形モードを指定
                })()
                
                # 複数モザイクタイプ処理
                selected_types = [key for key, value in self.config.mosaic_types.items() if value]
                for mosaic_type in selected_types:
                    # モザイクタイプ別設定を作成
                    type_config = type('obj', (object,), {
                        'bbox_expansion': 0,  # 拡張は既に適用済み
                        'use_fanza_standard': self.config.use_fanza_standard if mosaic_type == "block" else False,
                        'manual_tile_size': self.config.manual_tile_size,
                        'gaussian_blur_radius': self.config.gaussian_blur_radius,
                        'mode': 'rectangle'  # 矩形モードを指定
                    })()
                    
                    # シームレス処理（追加拡張なし）
                    result_none = self.mosaic_processor.apply(
                        image, bbox_masks, 
                        feather=self.config.feather, 
                        strength=1.0,  # 強度は固定値1.0を使用
                        config=type_config,
                        mosaic_type=mosaic_type
                    )
                    
                    # モザイクタイプ別サブフォルダに保存（出力フォルダ指定がない場合は入力画像フォルダを使用）
                    if self.output_dir:
                        type_output_dir = self.output_dir / mosaic_type
                    else:
                        type_output_dir = path.parent / mosaic_type
                    
                    type_output_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[DEBUG] Created subfolder: {type_output_dir}")
                    
                    output_path_none = get_custom_output_path(path, output_dir=type_output_dir, 
                                                            suffix="", config=self.config, 
                                                            counter=self.sequential_counter)
                    cv2.imwrite(str(output_path_none), result_none)
                    output_files.append((f"矩形マスク({mosaic_type})", output_path_none, len(bbox_masks)))
                    logger.info(f"  [矩形マスク-{mosaic_type}] -> {output_path_none}")
                
                mosaic_none_time = time.time() - mosaic_none_start
                
                # 連番カウンターを更新（連番モードの場合）
                if self.config.filename_mode == "sequential":
                    self.sequential_counter += 1
        
        mask_time = time.time() - mask_start
        logger.info(f"[Mask Generation & Processing] Time: {mask_time:.2f}s")
        
        # マスク方式比較結果
        if len(sam_results) > 1:
            vit_b_time = sam_results.get("ViT-B", {}).get("time", 0)
            none_time = sam_results.get("None", {}).get("time", 0)
            if vit_b_time > 0 and none_time > 0:
                speed_ratio = vit_b_time / none_time
                logger.info(f"[マスク方式比較] 輪郭マスク {vit_b_time:.1f}s vs 矩形マスク {none_time:.1f}s (輪郭マスクは {speed_ratio:.1f}倍時間)")
        elif sam_results:
            # Single method selected
            method_name = list(sam_results.keys())[0]
            method_time = list(sam_results.values())[0]["time"]
            method_display = "輪郭マスク" if method_name == "ViT-B" else "矩形マスク"
            logger.info(f"[マスク方式] {method_display} 処理時間: {method_time:.1f}s")
        
        if not output_files:
            self.progress_queue.put(("status", f"{path.name}: Mask generation failed"))
            self.progress_queue.put(("progress", (current, total)))
            return
        
        # Save visualization if requested
        if self.config.visualize:
            viz_start = time.time()
            vis_image = self.detector.visualize_detections(image, bboxes_with_class)
            
            # Detectionフォルダを各モザイクタイプと同階層に作成して保存
            if self.output_dir:
                detection_output_dir = self.output_dir / "Detection"
            else:
                detection_output_dir = path.parent / "Detection"
            
            detection_output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[DEBUG] Created detection folder: {detection_output_dir}")
            
            viz_path = get_custom_output_path(path, output_dir=detection_output_dir, 
                                            suffix="_viz", config=self.config, 
                                            counter=self.sequential_counter)
            cv2.imwrite(str(viz_path), vis_image)
            logger.info(f"  [Detection] -> {viz_path}")
            
            viz_time = time.time() - viz_start
            
            # 連番カウンターを更新（連番モードの場合）
            if self.config.filename_mode == "sequential":
                self.sequential_counter += 1
        
        total_time = time.time() - start_time
        logger.info(f"[Total Processing] Time: {total_time:.2f}s | Image: {path.name}")
        
        # Result summary with expansion info
        file_summary = ", ".join([f"{model}({masks} regions)" for model, _, masks in output_files])
        expansion_suffix = f" | 範囲{self.config.bbox_expansion:+d}px" if self.config.bbox_expansion != 0 else ""
        self.progress_queue.put(("status", f"{path.name}: Complete - {file_summary}{expansion_suffix} - {total_time:.1f}s"))
        self.progress_queue.put(("progress", (current, total)))
    

    
    def _select_output_folder(self):
        """Select output folder"""
        folder_path = filedialog.askdirectory(title="出力フォルダを選択")
        if folder_path:
            self.output_dir = Path(folder_path)
            self.output_dir_label.config(text=f"出力先: {self.output_dir.name}")
            self._add_status_message(f"出力フォルダを設定しました: {self.output_dir}")
            # ファイル名例示を更新
            self._update_filename_example()
    
    def _create_bbox_masks(self, image: np.ndarray, bboxes: List) -> List[np.ndarray]:
        """
        Create simple rectangular masks from bounding boxes (no SAM segmentation)
        
        Args:
            image: Input image
            bboxes: List of bounding boxes (x1, y1, x2, y2)
            
        Returns:
            List of binary masks for each bounding box
        """
        height, width = image.shape[:2]
        masks = []
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            
            # Create blank mask
            mask = np.zeros((height, width), dtype=np.uint8)
            
            # Fill rectangle area with 255
            mask[y1:y2, x1:x2] = 255
            
            masks.append(mask)
        
        logger.debug(f"Created {len(masks)} rectangular masks from bounding boxes")
        return masks
    
    def _initialize_models(self):
        """Initialize detection and segmentation models"""
        try:
            # GUI設定から現在のデバイス設定を取得
            current_device_mode = getattr(self, 'device_var', tk.StringVar(value="auto")).get()
            self.config.device_mode = current_device_mode
            
            # スマートなモデルセットアップを実行
            self._setup_models_smartly()
            
            # 選択されたモデルファイルでMultiModelDetectorを直接初期化（デバイス設定を渡す）
            self.detector = MultiModelDetector(config=self.config, device=self.config.device_mode)
            
            # Initialize selected segmentation models
            self.segmenter_vit_b = None
            
            if self.config.sam_use_vit_b:
                logger.info("Initializing SAM ViT-B model...")
                if not downloader.is_model_available("sam_vit_b"):
                    logger.info("Downloading SAM ViT-B model...")
                    success = downloader.download_model("sam_vit_b")
                    if not success:
                        raise RuntimeError("Failed to download SAM ViT-B model")
                # SAMにもデバイス設定を渡す
                self.segmenter_vit_b = GenitalSegmenter(model_type="vit_b", device=self.config.device_mode)
            
            # No initialization needed for "none" option - uses simple bounding box masks
            
            # Initialize mosaic processor
            self.mosaic_processor = MosaicProcessor()
            
            logger.info("All models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            
            # モデルファイルが見つからない場合の特別な処理
            if "検出用モデルファイルが見つかりません" in str(e):
                from tkinter import messagebox
                
                # スマートなモデルセットアップを再試行するかどうか確認
                result = messagebox.askyesno(
                    "モデルファイルが見つかりません", 
                    f"{str(e)}\n\n"
                    "スマートなモデルセットアップを実行しますか？\n"
                    "・自動ダウンロード可能なモデル → 自動でダウンロード\n"
                    "・手動ダウンロードが必要なモデル → ブラウザで開く",
                    icon='question'
                )
                
                if result:
                    try:
                        self._run_smart_model_setup()
                        return  # セットアップ後はアプリを継続
                    except Exception as setup_error:
                        logger.error(f"Smart model setup failed: {setup_error}")
                        messagebox.showerror("セットアップエラー", f"スマートセットアップに失敗しました：{setup_error}")
                
                # 従来のフォルダを開く選択肢も提供
                result2 = messagebox.askyesno(
                    "モデルフォルダを開きますか？", 
                    "手動でモデルファイルを配置する場合は、\n"
                    "モデル配置フォルダを開きますか？",
                    icon='question'
                )
                
                if result2:
                    try:
                        open_models_folder()
                        messagebox.showinfo(
                            "フォルダを開きました", 
                            "モデルファイルを配置後、アプリケーションを再起動してください。\n\n"
                            "必要なファイル:\n"
                            "• Anime NSFW Detection v4.0 (CivitAI)\n"
                            "• ZIPファイルを展開してanime_nsfw_v4フォルダに配置"
                        )
                    except Exception as folder_error:
                        logger.error(f"Failed to open models folder: {folder_error}")
                
                # アプリケーションを終了
                self.root.quit()
                return
            else:
                # その他のエラーは従来通り表示
                from tkinter import messagebox
                messagebox.showerror("エラー", f"モデルの初期化に失敗しました：{str(e)}")
                raise

    def _setup_models_smartly(self):
        """スマートなモデルセットアップの前チェック"""
        missing_info = downloader.get_missing_models_info()
        
        if not missing_info:
            logger.info("✅ All required models are already available")
            return
        
        logger.info("🔍 Some models are missing, will attempt smart setup if needed...")
        
        # 重要なモデル（anime_nsfw_v4）がない場合のみ警告
        if "anime_nsfw_v4" in missing_info:
            logger.warning("⚠️ Critical model (Anime NSFW Detection v4.0) is missing")

    def _run_smart_model_setup(self):
        """スマートなモデルセットアップを実行"""
        from tkinter import messagebox
        import threading
        import queue
        
        # CivitAI APIキー入力ダイアログ
        civitai_api_key = self._ask_civitai_api_key_main()
        
        # プログレスダイアログを作成
        progress_dialog = self._create_model_setup_dialog()
        
        # スレッド間通信用のキュー
        progress_queue = queue.Queue()
        
        # キャンセルフラグ
        self.model_setup_cancelled = False
        
        def setup_thread():
            """バックグラウンドでセットアップを実行"""
            try:
                def progress_callback(action: str, model_name: str, current: int, total: int):
                    """プログレス更新コールバック"""
                    try:
                        # キャンセルフラグをチェック
                        if self.model_setup_cancelled:
                            raise Exception("ユーザーによってキャンセルされました")
                        
                        progress_queue.put(("progress", action, model_name, current, total))
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                
                # ステータス更新
                progress_queue.put(("status", "モデルセットアップを開始しています...", 0, 100))
                
                # CivitAI APIキーを設定
                if civitai_api_key:
                    downloader.set_civitai_api_key(civitai_api_key)
                
                # スマートセットアップを実行
                results = downloader.smart_model_setup(progress_callback)
                
                # 結果をキューに送信
                progress_queue.put(("complete", results))
                
            except Exception as e:
                logger.error(f"Smart setup error: {e}")
                progress_queue.put(("error", str(e)))
        
        def check_progress():
            """プログレスキューをチェックして UI を更新"""
            try:
                processed_messages = 0
                max_messages_per_cycle = 10  # 1サイクルあたりの最大メッセージ処理数
                
                while processed_messages < max_messages_per_cycle:
                    message = progress_queue.get_nowait()
                    message_type = message[0]
                    
                    if message_type == "progress":
                        _, action, model_name, current, total = message
                        self._update_setup_progress(progress_dialog, action, model_name, current, total)
                    
                    elif message_type == "status":
                        _, status_text, current, total = message
                        self._update_setup_status(progress_dialog, status_text, current, total)
                    
                    elif message_type == "complete":
                        results = message[1]
                        self._handle_setup_results(progress_dialog, results)
                        return  # 完了時は monitoring を停止
                    
                    elif message_type == "error":
                        error_message = message[1]
                        self._handle_setup_error(progress_dialog, error_message)
                        return  # エラー時も monitoring を停止
                    
                    processed_messages += 1
                        
            except queue.Empty:
                pass
            
            # より頻繁にチェック（50ms間隔）
            if progress_dialog.winfo_exists() and not self.model_setup_cancelled:
                progress_dialog.after(50, check_progress)
        
        # キャンセルボタン機能を追加
        def cancel_setup():
            self.model_setup_cancelled = True
            progress_dialog.destroy()
        
        # キャンセルボタンを接続
        progress_dialog.cancel_button.config(command=cancel_setup)
        
        # バックグラウンドスレッドでセットアップ開始
        setup_thread_obj = threading.Thread(target=setup_thread, daemon=True)
        setup_thread_obj.start()
        
        # プログレス監視開始
        progress_dialog.after(50, check_progress)
        
        # プログレスダイアログを表示
        progress_dialog.wait_window()

    def _create_model_setup_dialog(self):
        """モデルセットアップ用のプログレスダイアログを作成"""
        dialog = tk.Toplevel(self.root)
        dialog.title("スマートモデルセットアップ")
        dialog.geometry("500x350")  # サイズを増加
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # ダイアログを中央に配置
        dialog.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
        
        # メインフレーム
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🤖 スマートモデルセットアップ", font=("", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 説明
        desc_label = ttk.Label(main_frame, text="モデルファイルの自動セットアップを実行中...", font=("", 10))
        desc_label.pack(pady=(0, 15))
        
        # プログレス表示エリア
        progress_frame = ttk.LabelFrame(main_frame, text="進捗状況", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 現在の作業表示
        current_label = ttk.Label(progress_frame, text="初期化中...", font=("", 10))
        current_label.pack(anchor=tk.W, pady=(0, 5))
        
        # プログレスバー（determinate mode に変更）
        progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # パーセンテージ表示
        percent_label = ttk.Label(progress_frame, text="0%", font=("", 9))
        percent_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 詳細ログエリア
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_text = tk.Text(log_frame, height=8, font=("Consolas", 9), wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
        log_text.config(yscrollcommand=log_scrollbar.set)
        
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # キャンセルボタン
        cancel_button = ttk.Button(main_frame, text="キャンセル")
        cancel_button.pack()
        
        # ダイアログに要素を保存
        dialog.current_label = current_label
        dialog.progress_bar = progress_bar
        dialog.percent_label = percent_label
        dialog.log_text = log_text
        dialog.cancel_button = cancel_button
        
        return dialog

    def _update_setup_progress(self, dialog, action: str, model_name: str, current: int, total: int):
        """セットアップ進捗を更新"""
        if not dialog.winfo_exists():
            return
        
        action_texts = {
            "downloading": f"📥 ダウンロード開始: {model_name}",
            "download_progress": f"📥 ダウンロード中: {model_name}",
            "download_complete": f"✅ 完了: {model_name}",
            "download_failed": f"❌ 失敗: {model_name}",
            "opening_browser": f"🌐 ブラウザで開いています: {model_name}",
            "browser_opened": f"✅ ブラウザで開きました: {model_name}",
            "browser_failed": f"❌ ブラウザ起動失敗: {model_name}",
            "extracting": f"📦 展開中: {model_name}",
        }
        
        current_text = action_texts.get(action, f"処理中: {model_name}")
        dialog.current_label.config(text=current_text)
        
        # プログレスバーの更新
        if total > 0:
            if action in ["download_complete", "download_failed"]:
                # ダウンロード完了時は100%表示
                dialog.progress_bar['value'] = 100
                dialog.percent_label.config(text="100%")
            elif action == "download_progress":
                # ダウンロード中は実際の進捗を表示
                percent = int((current / total) * 100)
                dialog.progress_bar['value'] = percent
                dialog.percent_label.config(text=f"{percent}%")
                
                # ダウンロードサイズの表示
                if total > 1024:
                    current_mb = current / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    size_text = f" ({current_mb:.1f}/{total_mb:.1f} MB)"
                    dialog.current_label.config(text=current_text + size_text)
            else:
                # その他の場合は通常の計算
                percent = int((current / total) * 100)
                dialog.progress_bar['value'] = percent
                dialog.percent_label.config(text=f"{percent}%")
        
        # ログの1行更新機能
        timestamp = time.strftime("%H:%M:%S")
        
        if action == "download_progress":
            # ダウンロード進捗は1行で更新
            percent = int((current / total) * 100) if total > 0 else 0
            if total > 1024:
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                log_message = f"[{timestamp}] [download_progress] {model_name} - {percent}% ({current_mb:.1f}/{total_mb:.1f} MB)"
            else:
                log_message = f"[{timestamp}] [download_progress] {model_name} - {percent}%"
            
            # 最後の行が同じモデルのダウンロード進捗なら更新、そうでなければ新規追加
            if hasattr(dialog, '_last_progress_model') and dialog._last_progress_model == model_name:
                # 最後の行を削除して新しい進捗で更新
                dialog.log_text.delete("end-2l", "end-1l")
                dialog.log_text.insert(tk.END, log_message + "\n")
            else:
                # 新しいモデルの場合は新規追加
                dialog.log_text.insert(tk.END, log_message + "\n")
                dialog._last_progress_model = model_name
        else:
            # その他のアクションは通常通り追加
            log_message = f"[{timestamp}] [{action}] {model_name}"
            dialog.log_text.insert(tk.END, log_message + "\n")
            
            # ダウンロード完了時は進捗追跡をリセット
            if action in ["download_complete", "download_failed"]:
                dialog._last_progress_model = None
        
        dialog.log_text.see(tk.END)
        
        # UIを強制更新
        dialog.update_idletasks()
        
        # 次のモデルに移行する際はプログレスバーをリセット
        if action in ["download_complete", "download_failed"]:
            # 少し待ってからプログレスバーをリセット
            dialog.after(1000, lambda: self._reset_main_progress_for_next_model(dialog))

    def _reset_main_progress_for_next_model(self, dialog):
        """次のモデルのためにプログレスバーをリセット（メインGUI用）"""
        if dialog.winfo_exists():
            dialog.progress_bar['value'] = 0
            dialog.percent_label.config(text="0%")

    def _update_setup_status(self, dialog, status_text: str, current: int, total: int):
        """セットアップのステータスを更新"""
        if not dialog.winfo_exists():
            return
        
        dialog.current_label.config(text=status_text)
        
        if total > 0:
            percent = int((current / total) * 100)
            dialog.progress_bar['value'] = percent
            dialog.percent_label.config(text=f"{percent}%")
        
        # ログに追加
        timestamp = time.strftime("%H:%M:%S")
        dialog.log_text.insert(tk.END, f"[{timestamp}] [STATUS] {status_text}\n")
        dialog.log_text.see(tk.END)
        
        # UIを強制更新
        dialog.update_idletasks()

    def _handle_setup_results(self, dialog, results: Dict):
        """セットアップ結果を処理"""
        from tkinter import messagebox
        
        if not dialog.winfo_exists():
            return
        
        dialog.destroy()
        
        # 結果のサマリーを表示
        summary_lines = []
        
        if results.get("success", []):
            summary_lines.append(f"✅ 自動ダウンロード完了: {len(results['success'])}個")
            summary_lines.extend([f"  • {model}" for model in results["success"]])
        
        if results.get("already_available", []):
            summary_lines.append(f"✅ 既に利用可能: {len(results['already_available'])}個")
            summary_lines.extend([f"  • {model}" for model in results["already_available"]])
        
        if results.get("manual_required", []):
            summary_lines.append(f"🌐 手動ダウンロードが必要: {len(results['manual_required'])}個")
            summary_lines.extend([f"  • {model}" for model in results["manual_required"]])
        
        if results.get("failed", []):
            summary_lines.append(f"❌ 失敗: {len(results['failed'])}個")
            summary_lines.extend([f"  • {model}" for model in results["failed"]])
        
        summary_text = "\n".join(summary_lines)
        
        if results.get("manual_required", []):
            messagebox.showinfo(
                "スマートセットアップ完了",
                f"モデルセットアップが完了しました！\n\n"
                f"{summary_text}\n\n"
                "【次の手順】\n"
                "1. 手動ダウンロードが必要なモデルがあります\n"
                "2. メニューの「モデル管理」→「スマートセットアップ」で再試行\n"
                "3. または手動でZIPファイルをダウンロードして配置\n\n"
                "配置方法の詳細は配布用README.mdをご確認ください。"
            )
        else:
            messagebox.showinfo(
                "スマートセットアップ完了",
                f"モデルセットアップが完了しました！\n\n{summary_text}"
            )

    def _handle_setup_error(self, dialog, error_message: str):
        """セットアップエラーを処理"""
        from tkinter import messagebox
        
        if not dialog.winfo_exists():
            return
        
        dialog.destroy()
        
        messagebox.showerror(
            "セットアップエラー",
            f"スマートセットアップ中にエラーが発生しました：\n\n{error_message}\n\n"
            "手動でモデルファイルを配置してください。"
        )
    
    def _on_mosaic_type_change(self):
        """Handle mosaic type change"""
        # 選択されたモザイクタイプを取得
        selected_types = [key for key, var in self.mosaic_type_vars.items() if var.get()]
        
        # 少なくとも1つは選択必須
        if not selected_types:
            # 最後に変更されたチェックボックスを強制的にONにする
            self.mosaic_type_vars["block"].set(True)
            selected_types = ["block"]
            from tkinter import messagebox
            messagebox.showwarning("選択必須", "少なくとも1つの処理オプションを選択してください。\nブロックモザイクを自動選択しました。")
        
        # FANZA対応状況の更新
        has_fanza_compatible = "block" in selected_types
        has_fanza_incompatible = any(t in selected_types for t in ["gaussian", "white", "black"])
        
        # 各設定欄の表示制御
        has_block = "block" in selected_types
        has_gaussian = "gaussian" in selected_types
        has_fill = any(t in selected_types for t in ["white", "black"])
        
        # ブロックモザイク設定の表示制御
        if has_block:
            self.block_size_label.config(foreground="black")
            if has_fanza_compatible and (self.use_fanza_var.get() if hasattr(self, 'use_fanza_var') else False):
                self.manual_tile_spin.config(state=tk.DISABLED)
                self.block_unit_label.config(text="px（FANZA基準を無効にした場合のみ有効）", foreground="gray")
            else:
                self.manual_tile_spin.config(state=tk.NORMAL)
                self.block_unit_label.config(text="px（手動設定）", foreground="gray")
        else:
            self.block_size_label.config(foreground="gray")
            self.manual_tile_spin.config(state=tk.DISABLED)
            self.block_unit_label.config(text="px（未選択）", foreground="gray")
        
        # ガウスモザイク設定の表示制御
        if has_gaussian:
            self.gaussian_size_label.config(foreground="black")
            self.gaussian_blur_spin.config(state=tk.NORMAL)
            self.gaussian_unit_label.config(text="px（ぼかし半径、FANZA非対応）", foreground="gray")
        else:
            self.gaussian_size_label.config(foreground="gray")
            self.gaussian_blur_spin.config(state=tk.DISABLED)
            self.gaussian_unit_label.config(text="px（未選択）", foreground="gray")
        
        # FANZA基準の制御
        if has_fanza_compatible and has_fanza_incompatible:
            # FANZA対応と非対応が混在
            self.fanza_info_label.config(text="⚠️ FANZA対応（ブロック）と非対応（その他）が混在しています", foreground="orange")
            # チェックボックスは有効化するが、強制的に設定はしない
            self.fanza_check.config(state=tk.NORMAL)
        elif has_fanza_compatible:
            # FANZA対応のみ
            self.fanza_info_label.config(text="✅ 選択された処理はFANZA基準に対応しています", foreground="green")
            # チェックボックスは有効化するが、強制的に設定はしない
            self.fanza_check.config(state=tk.NORMAL)
        else:
            # FANZA非対応のみ
            non_fanza_types = [t for t in selected_types if t in ["gaussian", "white", "black"]]
            self.fanza_info_label.config(text=f"❌ 選択された処理（{', '.join(non_fanza_types)}）はFANZA非対応です", foreground="red")
            # FANZA非対応の場合のみ強制的にOFFにして無効化
            self.use_fanza_var.set(False)
            self.fanza_check.config(state=tk.DISABLED)
    
    def _on_fanza_toggle(self):
        """Handle FANZA standard toggle"""
        # FANZA基準の変更に応じてモザイクサイズ設定を更新
        selected_types = [key for key, var in self.mosaic_type_vars.items() if var.get()]
        has_block = "block" in selected_types
        
        # ブロックモザイク設定の表示制御のみ更新
        if has_block:
            if self.use_fanza_var.get():
                self.manual_tile_spin.config(state=tk.DISABLED)
                self.block_unit_label.config(text="px（FANZA基準を無効にした場合のみ有効）", foreground="gray")
            else:
                self.manual_tile_spin.config(state=tk.NORMAL)
                self.block_unit_label.config(text="px（手動設定）", foreground="gray")
    
    def _update_filename_example(self):
        """Update filename example"""
        mode = self.filename_mode_var.get()
        
        if mode == "original":
                self.filename_example_label.config(text="例: image001.jpg", foreground="gray")
        elif mode == "prefix":
            prefix = self.prefix_var.get()
            self.filename_example_label.config(text=f"例: {prefix}image001.jpg", foreground="gray")
        elif mode == "sequential":
            prefix = self.seq_prefix_var.get()
            start_number = self.seq_start_var.get()
            self.filename_example_label.config(text=f"例: {prefix}{start_number}.jpg", foreground="gray")
    
    def _on_individual_expansion_toggle(self):
        """Handle individual expansion toggle"""
        if self.use_individual_expansion_var.get():
            # 個別設定を有効化
            for widget in self.individual_frame.winfo_children():
                for subwidget in widget.winfo_children():
                    if isinstance(subwidget, ttk.Spinbox):
                        subwidget.configure(state=tk.NORMAL)
        else:
            # 個別設定を無効化
            for widget in self.individual_frame.winfo_children():
                for subwidget in widget.winfo_children():
                    if isinstance(subwidget, ttk.Spinbox):
                        subwidget.configure(state=tk.DISABLED)
    
    def run(self):
        """Run the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            from tkinter import messagebox
            messagebox.showerror("エラー", f"アプリケーションエラー: {str(e)}")

    def _ask_civitai_api_key_main(self):
        """CivitAI APIキーの入力を求める（メインGUI用）"""
        # カスタムダイアログを作成
        api_key_dialog = tk.Toplevel(self.root)
        api_key_dialog.title("CivitAI APIキー")
        api_key_dialog.geometry("450x300")
        api_key_dialog.resizable(False, False)
        api_key_dialog.transient(self.root)
        api_key_dialog.grab_set()
        
        # ダイアログを中央に配置
        api_key_dialog.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
        
        result = {"api_key": None}
        
        # メインフレーム
        main_frame = ttk.Frame(api_key_dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🔑 CivitAI APIキー設定", font=("", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 説明テキスト
        desc_text = tk.Text(main_frame, height=10, wrap=tk.WORD, font=("", 9))
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        desc_content = (
            "CivitAI APIキーをお持ちですか？\n\n"
            "【APIキーがある場合】\n"
            "✅ Anime NSFW Detection v4.0 を自動ダウンロード\n"
            "✅ より高速で確実なダウンロード\n"
            "✅ 手動操作が不要\n\n"
            "【APIキーがない場合】\n"
            "🌐 ブラウザでCivitAIページを開きます\n"
            "📥 手動でダウンロードしてください\n\n"
            "【APIキーの取得方法】\n"
            "1. CivitAI にログイン\n"
            "2. プロフィール → Account Settings → API Keys\n"
            "3. 「Add API Key」でキーを生成\n\n"
            "APIキーを入力してください (持っていない場合は空白のままOK):"
        )
        
        desc_text.insert("1.0", desc_content)
        desc_text.config(state=tk.DISABLED)
        
        # APIキー入力フィールド
        key_frame = ttk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(key_frame, text="APIキー:").pack(anchor=tk.W)
        api_key_entry = ttk.Entry(key_frame, width=50)  # show="*"を削除
        api_key_entry.pack(fill=tk.X, pady=(5, 0))
        
        # 右クリックメニューを追加
        def show_context_menu(event):
            """右クリック時にコンテキストメニューを表示"""
            # メニューを毎回新しく作成
            context_menu = tk.Menu(api_key_dialog, tearoff=0)
            
            def paste_text():
                """クリップボードからテキストをペースト"""
                try:
                    clipboard_text = api_key_entry.clipboard_get()
                    # 現在の選択範囲を削除してペースト
                    if api_key_entry.selection_present():
                        api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    api_key_entry.insert(tk.INSERT, clipboard_text)
                except tk.TclError:
                    # クリップボードが空の場合
                    pass
            
            def copy_text():
                """選択されたテキストをクリップボードにコピー"""
                try:
                    if api_key_entry.selection_present():
                        selected_text = api_key_entry.selection_get()
                        api_key_entry.clipboard_clear()
                        api_key_entry.clipboard_append(selected_text)
                except tk.TclError:
                    pass
            
            def cut_text():
                """選択されたテキストを切り取り"""
                try:
                    if api_key_entry.selection_present():
                        selected_text = api_key_entry.selection_get()
                        api_key_entry.clipboard_clear()
                        api_key_entry.clipboard_append(selected_text)
                        api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
            
            def select_all():
                """全てのテキストを選択"""
                api_key_entry.select_range(0, tk.END)
                api_key_entry.icursor(tk.END)
            
            # メニュー項目を追加
            context_menu.add_command(label="切り取り", command=cut_text)
            context_menu.add_command(label="コピー", command=copy_text)
            context_menu.add_command(label="貼り付け", command=paste_text)
            context_menu.add_separator()
            context_menu.add_command(label="すべて選択", command=select_all)
            
            # メニューを表示
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception as e:
                print(f"Context menu error: {e}")
            finally:
                # メニューを解放
                context_menu.grab_release()
        
        # 右クリックイベントをバインド
        api_key_entry.bind("<Button-3>", show_context_menu)
        
        # Ctrl+V でのペーストも有効化
        def handle_paste(event):
            """Ctrl+V でのペースト処理"""
            try:
                clipboard_text = api_key_entry.clipboard_get()
                if api_key_entry.selection_present():
                    api_key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                api_key_entry.insert(tk.INSERT, clipboard_text)
                return "break"  # デフォルトの処理を無効化
            except tk.TclError:
                pass
        
        api_key_entry.bind("<Control-v>", handle_paste)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            result["api_key"] = api_key_entry.get().strip() or None
            api_key_dialog.destroy()
        
        def on_cancel():
            result["api_key"] = None
            api_key_dialog.destroy()
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="スキップ", command=on_cancel).pack(side=tk.LEFT)
        
        # エンターキーでOK
        api_key_entry.bind('<Return>', lambda e: on_ok())
        api_key_entry.focus()
        
        # ダイアログを表示
        api_key_dialog.wait_window()
        
        return result["api_key"]

def main():
    """Main entry point"""
    app = AutoMosaicGUI()
    app.run()

if __name__ == "__main__":
    main() 