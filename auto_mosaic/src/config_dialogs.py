"""
設定プロファイル管理用ダイアログ
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ConfigSaveDialog:
    """設定保存ダイアログ"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
    def show(self) -> Optional[Tuple[str, str]]:
        """ダイアログを表示して結果を返す"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("設定プロファイルを保存")
        self.dialog.geometry("500x400")
        self.dialog.minsize(480, 380)  # 最小サイズを設定
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # ダイアログを親ウィンドウの中央に配置
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_widgets()
        
        # ダイアログが閉じられるまで待機
        self.dialog.wait_window()
        
        return self.result
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="設定プロファイルを保存", 
                               font=("", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # プロファイル名入力
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(name_frame, text="プロファイル名:").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, font=("", 10))
        self.name_entry.pack(fill=tk.X, pady=(5, 0))
        self.name_entry.focus()
        
        # 説明入力
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(desc_frame, text="説明（省略可）:").pack(anchor=tk.W)
        
        # テキストエリアをスクロールバー付きフレームで包む
        text_container = ttk.Frame(desc_frame)
        text_container.pack(fill=tk.X, pady=(5, 0))
        
        self.desc_text = tk.Text(text_container, height=4, font=("", 9))
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.desc_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.config(yscrollcommand=scrollbar.set)
        
        # 既存プロファイル一覧（簡素化）
        existing_frame = ttk.LabelFrame(main_frame, text="既存のプロファイル", padding="5")
        existing_frame.pack(fill=tk.X, pady=(0, 10))
        
        profiles = self.config_manager.get_profile_list()
        if profiles:
            # 最大2つまで表示してスペースを節約
            display_profiles = profiles[:2]
            profile_names = [p['name'] for p in display_profiles]
            profile_text = "• " + ", ".join(profile_names)
            if len(profiles) > 2:
                profile_text += f" 他{len(profiles)-2}個"
            
            ttk.Label(existing_frame, text=profile_text, foreground="gray", 
                     wraplength=450).pack(anchor=tk.W)
        else:
            ttk.Label(existing_frame, text="保存済みプロファイルはありません", 
                     foreground="gray").pack(anchor=tk.W)
        
        # ボタン（最下部に固定配置）
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))
        
        # ボタンを中央寄せで配置
        button_container = ttk.Frame(button_frame)
        button_container.pack(anchor=tk.CENTER)
        
        # 保存ボタン（デフォルト、目立つように左側に配置）
        save_btn = ttk.Button(button_container, text="💾 保存", command=self._save, width=12)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # キャンセルボタン
        cancel_btn = ttk.Button(button_container, text="キャンセル", command=self._cancel, width=12)
        cancel_btn.pack(side=tk.LEFT)
        
        # 保存ボタンをデフォルトボタンとして設定
        self.dialog.bind('<Return>', lambda e: self._save())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
        
        # 最初は名前入力フィールドにフォーカスを設定
        self.name_entry.focus_set()
    
    def _save(self):
        """保存処理"""
        name = self.name_var.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not name:
            messagebox.showerror("エラー", "プロファイル名を入力してください。")
            self.name_entry.focus()
            return
        
        # 無効な文字チェック
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in name for char in invalid_chars):
            messagebox.showerror("エラー", 
                               f"プロファイル名に次の文字は使用できません:\n{' '.join(invalid_chars)}")
            self.name_entry.focus()
            return
        
        # 既存プロファイルとの重複チェック
        existing_profiles = [p['name'] for p in self.config_manager.get_profile_list()]
        if name in existing_profiles:
            result = messagebox.askyesno("確認", 
                                       f"プロファイル '{name}' は既に存在します。\n上書きしますか？")
            if not result:
                self.name_entry.focus()
                return
        
        self.result = (name, description)
        self.dialog.destroy()
    
    def _cancel(self):
        """キャンセル処理"""
        self.result = None
        self.dialog.destroy()


class ConfigLoadDialog:
    """設定読み込みダイアログ"""
    
    def __init__(self, parent, config_manager, title="設定プロファイルを読み込み"):
        self.parent = parent
        self.config_manager = config_manager
        self.title = title
        self.result = None
        
    def show(self) -> Optional[str]:
        """ダイアログを表示して結果を返す"""
        profiles = self.config_manager.get_profile_list()
        if not profiles:
            messagebox.showinfo("情報", "保存済みの設定プロファイルがありません。")
            return None
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("650x450")
        self.dialog.minsize(600, 400)  # 最小サイズを設定
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # ダイアログを親ウィンドウの中央に配置
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_widgets()
        
        # ダイアログが閉じられるまで待機
        self.dialog.wait_window()
        
        return self.result
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text=self.title, 
                               font=("", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # プロファイル一覧
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Treeview（テーブル）
        columns = ("name", "description", "modified")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        # カラムの設定
        self.tree.heading("name", text="プロファイル名")
        self.tree.heading("description", text="説明")
        self.tree.heading("modified", text="更新日時")
        
        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("description", width=250, minwidth=150)
        self.tree.column("modified", width=150, minwidth=100)
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 配置
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        # プロファイルデータを挿入
        profiles = self.config_manager.get_profile_list()
        for profile in profiles:
            # 日時フォーマット
            try:
                from datetime import datetime
                modified_dt = datetime.fromisoformat(profile['modified_at'])
                modified_str = modified_dt.strftime("%Y/%m/%d %H:%M")
            except:
                modified_str = profile['modified_at'][:16] if len(profile['modified_at']) > 16 else profile['modified_at']
            
            # 説明の長さ制限
            desc = profile['description']
            if len(desc) > 50:
                desc = desc[:47] + "..."
            
            item_id = self.tree.insert("", tk.END, values=(
                profile['name'],
                desc,
                modified_str
            ))
            
            # 現在のプロファイルを強調表示
            if profile.get('is_current', False):
                self.tree.set(item_id, "name", f"★ {profile['name']}")
        
        # ダブルクリックで読み込み
        self.tree.bind('<Double-1>', lambda e: self._load())
        
        # ボタン（最下部に固定配置）
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))
        
        # ボタンを中央寄せで配置
        button_container = ttk.Frame(button_frame)
        button_container.pack(anchor=tk.CENTER)
        
        # 読み込みボタン（デフォルト）
        load_btn = ttk.Button(button_container, text="📂 読み込み", command=self._load, width=12)
        load_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # キャンセルボタン
        cancel_btn = ttk.Button(button_container, text="キャンセル", command=self._cancel, width=12)
        cancel_btn.pack(side=tk.LEFT)
        
        # キーボードショートカット設定
        self.dialog.bind('<Return>', lambda e: self._load())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
    
    def _load(self):
        """読み込み処理"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "プロファイルを選択してください。")
            return
        
        # 選択されたプロファイル名を取得
        item = selection[0]
        name = self.tree.item(item, "values")[0]
        
        # ★マークを除去
        if name.startswith("★ "):
            name = name[2:]
        
        self.result = name
        self.dialog.destroy()
    
    def _cancel(self):
        """キャンセル処理"""
        self.result = None
        self.dialog.destroy()


class ProfileManagerDialog:
    """プロファイル管理ダイアログ"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
    def show(self) -> Optional[str]:
        """ダイアログを表示して結果を返す"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("プロファイル管理")
        self.dialog.geometry("700x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # ダイアログを親ウィンドウの中央に配置
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_widgets()
        self._refresh_list()
        
        # ダイアログが閉じられるまで待機
        self.dialog.wait_window()
        
        return self.result
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="プロファイル管理", 
                               font=("", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # メインコンテンツ
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # プロファイル一覧（左側）
        list_frame = ttk.LabelFrame(content_frame, text="保存済みプロファイル", padding="10")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Treeview
        columns = ("name", "description", "modified")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("name", text="名前")
        self.tree.heading("description", text="説明")
        self.tree.heading("modified", text="更新日時")
        
        self.tree.column("name", width=120, minwidth=80)
        self.tree.column("description", width=180, minwidth=100)
        self.tree.column("modified", width=120, minwidth=80)
        
        # スクロールバー
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作ボタン（右側）
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(button_frame, text="📂 読み込み", width=15,
                  command=self._load_profile).pack(pady=(0, 5))
        
        ttk.Button(button_frame, text="📝 名前変更", width=15,
                  command=self._rename_profile).pack(pady=(0, 5))
        
        ttk.Button(button_frame, text="📄 複製", width=15,
                  command=self._duplicate_profile).pack(pady=(0, 5))
        
        ttk.Button(button_frame, text="🗑️ 削除", width=15,
                  command=self._delete_profile).pack(pady=(0, 20))
        
        ttk.Button(button_frame, text="📤 エクスポート", width=15,
                  command=self._export_profile).pack(pady=(0, 5))
        
        ttk.Button(button_frame, text="🔄 更新", width=15,
                  command=self._refresh_list).pack(pady=(0, 5))
        
        # 閉じるボタン
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(fill=tk.X, pady=(15, 0))
        
        # ボタンを中央寄せで配置
        close_container = ttk.Frame(close_frame)
        close_container.pack(anchor=tk.CENTER)
        
        ttk.Button(close_container, text="閉じる", command=self._close, width=12).pack()
        
        # キーボードショートカット設定
        self.dialog.bind('<Escape>', lambda e: self._close())
    
    def _refresh_list(self):
        """プロファイル一覧を更新"""
        # 既存のアイテムを削除
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # プロファイルデータを挿入
        profiles = self.config_manager.get_profile_list()
        for profile in profiles:
            # 日時フォーマット
            try:
                from datetime import datetime
                modified_dt = datetime.fromisoformat(profile['modified_at'])
                modified_str = modified_dt.strftime("%m/%d %H:%M")
            except:
                modified_str = profile['modified_at'][:16] if len(profile['modified_at']) > 16 else profile['modified_at']
            
            # 説明の長さ制限
            desc = profile['description']
            if len(desc) > 30:
                desc = desc[:27] + "..."
            
            name = profile['name']
            if profile.get('is_current', False):
                name = f"★ {name}"
            
            self.tree.insert("", tk.END, values=(name, desc, modified_str))
    
    def _get_selected_profile(self) -> Optional[str]:
        """選択されたプロファイル名を取得"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "プロファイルを選択してください。")
            return None
        
        item = selection[0]
        name = self.tree.item(item, "values")[0]
        
        # ★マークを除去
        if name.startswith("★ "):
            name = name[2:]
        
        return name
    
    def _load_profile(self):
        """プロファイルを読み込み"""
        name = self._get_selected_profile()
        if name:
            self.result = name
            self.dialog.destroy()
    
    def _rename_profile(self):
        """プロファイル名を変更"""
        old_name = self._get_selected_profile()
        if not old_name:
            return
        
        # 新しい名前を入力
        new_name = tk.simpledialog.askstring(
            "名前変更", 
            f"新しい名前を入力してください:",
            initialvalue=old_name
        )
        
        if new_name and new_name != old_name:
            # 既存プロファイルを取得
            profiles = self.config_manager.get_profile_list()
            target_profile = None
            for profile in profiles:
                if profile['name'] == old_name:
                    target_profile = profile
                    break
            
            if target_profile:
                # 新しい名前で保存
                profile_obj = self.config_manager.profiles[old_name]
                config = self.config_manager.dict_to_processing_config(profile_obj.config_data)
                
                if self.config_manager.save_profile(new_name, config, profile_obj.description):
                    # 古いプロファイルを削除
                    self.config_manager.delete_profile(old_name)
                    self._refresh_list()
                    messagebox.showinfo("完了", f"'{old_name}' を '{new_name}' に変更しました。")
                else:
                    messagebox.showerror("エラー", "名前の変更に失敗しました。")
    
    def _duplicate_profile(self):
        """プロファイルを複製"""
        name = self._get_selected_profile()
        if not name:
            return
        
        # 複製名を生成
        new_name = f"{name}_コピー"
        counter = 1
        existing_names = [p['name'] for p in self.config_manager.get_profile_list()]
        while new_name in existing_names:
            new_name = f"{name}_コピー{counter}"
            counter += 1
        
        # 複製を作成
        if name in self.config_manager.profiles:
            profile_obj = self.config_manager.profiles[name]
            config = self.config_manager.dict_to_processing_config(profile_obj.config_data)
            
            if self.config_manager.save_profile(new_name, config, f"{profile_obj.description} (複製)"):
                self._refresh_list()
                messagebox.showinfo("完了", f"'{name}' を '{new_name}' として複製しました。")
            else:
                messagebox.showerror("エラー", "複製に失敗しました。")
    
    def _delete_profile(self):
        """プロファイルを削除"""
        name = self._get_selected_profile()
        if not name:
            return
        
        result = messagebox.askyesno(
            "削除確認", 
            f"プロファイル '{name}' を削除しますか？\n\nこの操作は元に戻せません。"
        )
        
        if result:
            if self.config_manager.delete_profile(name):
                self._refresh_list()
                messagebox.showinfo("完了", f"プロファイル '{name}' を削除しました。")
            else:
                messagebox.showerror("エラー", "削除に失敗しました。")
    
    def _export_profile(self):
        """プロファイルをエクスポート"""
        name = self._get_selected_profile()
        if not name:
            return
        
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="設定をエクスポート",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{name}_config.json"
        )
        
        if file_path:
            if self.config_manager.export_profile(name, file_path):
                messagebox.showinfo("エクスポート完了", f"設定を {file_path} にエクスポートしました。")
            else:
                messagebox.showerror("エラー", "エクスポートに失敗しました。")
    
    def _close(self):
        """ダイアログを閉じる"""
        self.result = None
        self.dialog.destroy()


# 簡易入力ダイアログ（tkinter.simpledialogの代替）
import tkinter.simpledialog