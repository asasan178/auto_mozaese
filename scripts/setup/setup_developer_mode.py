#!/usr/bin/env python3
"""
開発者モード・特定ユーザー設定ユーティリティ
認証方式切り替え機能の有効化/無効化を管理するスクリプト
"""

import sys
import json
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_developer_mode():
    """開発者モードを有効にする"""
    try:
        from auto_mosaic.src.auth_config import AuthConfig
        
        auth_config = AuthConfig()
        
        print("🛠️ 開発者モード設定")
        print("=" * 40)
        
        # 現在の状態確認
        current_dev_mode = auth_config.is_developer_mode()
        current_switching = auth_config.is_auth_method_switching_available()
        
        print(f"現在の開発者モード: {'有効' if current_dev_mode else '無効'}")
        print(f"現在の認証切り替え: {'利用可能' if current_switching else '利用不可'}")
        print()
        
        if current_dev_mode:
            print("✅ 既に開発者モードが有効です。")
            
            choice = input("再設定しますか？ (y/N): ").lower()
            if choice != 'y':
                return
        
        print("開発者モードを有効にする方法:")
        print("🔧 .envファイル設定（統一方式）")
        print()
        print(".envファイルに以下の設定を追加してください:")
        print("DEVELOPER_MODE=true")
        print()
        print("💡 これにより以下の機能が有効になります:")
        print("  - 月次パスワード認証")
        print("  - 認証方式切り替えUI")
        print("  - 開発者向け機能")
        print()
        
        # .envファイルの場所を表示
        import os
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            print(f"📁 既存の.envファイル: {env_file.absolute()}")
            print("   ファイルを編集してDEVELOPER_MODE=trueを追加または変更してください。")
        else:
            print(f"📁 .envファイルを作成してください: {env_file.absolute()}")
            print("   ファイルを新規作成してDEVELOPER_MODE=trueを設定してください。")
        
        print()
        choice = input("設定完了後にEnterキーを押してください...")
        
        print("\n🎉 設定完了！アプリケーションを再起動すると開発者モードが有効になります。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def setup_special_user():
    """特定ユーザー設定を作成する"""
    try:
        from auto_mosaic.src.auth_config import AuthConfig
        
        auth_config = AuthConfig()
        
        print("👤 特定ユーザー設定")
        print("=" * 40)
        
        # 開発者モードチェック
        if not auth_config.is_developer_mode():
            print("⚠️ 開発者モードが無効です。")
            print("特定ユーザー設定を作成するには、まず開発者モードを有効にしてください。")
            
            enable_dev = input("開発者モードを有効にしますか？ (y/N): ").lower()
            if enable_dev == 'y':
                setup_developer_mode()
                print("\n" + "=" * 40)
            else:
                return
        
        print("特定ユーザー設定を作成します。")
        print()
        
        # ユーザー種別の入力
        print("ユーザー種別の例:")
        print("  - tester: テストユーザー")
        print("  - beta_user: ベータテストユーザー")
        print("  - reviewer: レビューアー")
        print("  - developer: 開発者")
        
        user_type = input("\nユーザー種別を入力してください: ").strip()
        if not user_type:
            print("❌ ユーザー種別が入力されていません。")
            return
        
        # 認証切り替え許可の確認
        print()
        print("認証方式切り替え許可:")
        print("  - Yes: 月次パスワード認証とDiscord認証を切り替え可能")
        print("  - No: Discord認証のみ使用可能")
        
        allow_switching_input = input("認証方式の切り替えを許可しますか？ (y/N): ").lower()
        allow_switching = allow_switching_input == 'y'
        
        # 統一化により特定ユーザー設定は廃止
        print("\n💡 統一化により特定ユーザー設定は廃止されました。")
        print("開発者モードは .env の DEVELOPER_MODE 設定のみで制御されます。")
        print()
        print("現在の開発者モード状態:")
        print(f"  開発者モード: {'✅ 有効' if auth_config.is_developer_mode() else '❌ 無効'}")
        print(f"  認証切り替え: {'✅ 利用可能' if auth_config.is_auth_method_switching_available() else '❌ 利用不可'}")
        
        if not auth_config.is_developer_mode():
            print()
            print("開発者モードを有効にするには、.envファイルで以下を設定してください:")
            print("DEVELOPER_MODE=true")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def check_current_status():
    """現在の認証設定状態を確認する"""
    try:
        from auto_mosaic.src.auth_config import AuthConfig
        import sys
        import os
        import getpass
        
        auth_config = AuthConfig()
        
        print("🔍 現在の認証設定状態")
        print("=" * 50)
        
        # 基本情報
        print("=== 基本情報 ===")
        print(f"実行環境: {'開発環境 (Python)' if not getattr(sys, 'frozen', False) else 'exe化環境'}")
        print(f"ユーザー名: {getpass.getuser()}")
        print(f"設定ディレクトリ: {auth_config.config_dir}")
        print()
        
        # 開発者モード関連
        print("=== 開発者モード ===")
        print(f"開発者モード: {'✅ 有効' if auth_config.is_developer_mode() else '❌ 無効'}")
        print(f"認証切り替え: {'✅ 利用可能' if auth_config.is_auth_method_switching_available() else '❌ 利用不可'}")
        print(f"特定ユーザー: {'✅ Yes' if auth_config._is_special_user() else '❌ No'}")
        print()
        
        # 環境変数
        print("=== 環境変数 ===")
        dev_mode_env = os.getenv('AUTO_MOSAIC_DEV_MODE', '未設定')
        print(f"AUTO_MOSAIC_DEV_MODE: {dev_mode_env}")
        print()
        
        # ファイル存在チェック
        print("=== 設定ファイル ===")
        files_to_check = [
            ("auth_config.json", auth_config.config_file),
            ("developer_mode.txt", auth_config.config_dir / "developer_mode.txt"),
            ("debug_mode.enabled", auth_config.config_dir / "debug_mode.enabled"),
            (".developer", auth_config.app_data_dir / ".developer"),
            ("master_access.key", auth_config.config_dir / "master_access.key"),
            ("special_user.json", auth_config.config_dir / "special_user.json"),
        ]
        
        for file_name, file_path in files_to_check:
            status = "✅ 存在" if file_path.exists() else "❌ なし"
            print(f"{file_name}: {status}")
        
        # 現在の認証設定
        print()
        print("=== 現在の認証設定 ===")
        try:
            current_method = auth_config.get_auth_method()
            print(f"認証方式: {current_method.value}")
            
            last_method = auth_config.get_last_successful_method()
            if last_method:
                print(f"最後に成功した方式: {last_method.value}")
            else:
                print("最後に成功した方式: なし")
        except Exception as e:
            print(f"認証設定の読み込みエラー: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ 状態確認エラー: {e}")
        import traceback
        traceback.print_exc()

def remove_developer_settings():
    """開発者設定を削除する"""
    try:
        from auto_mosaic.src.auth_config import AuthConfig
        
        auth_config = AuthConfig()
        
        print("🗑️ 開発者設定の削除")
        print("=" * 40)
        
        print("以下の設定ファイルを削除します:")
        files_to_remove = [
            ("developer_mode.txt", auth_config.config_dir / "developer_mode.txt"),
            ("debug_mode.enabled", auth_config.config_dir / "debug_mode.enabled"),
            (".developer", auth_config.app_data_dir / ".developer"),
            ("master_access.key", auth_config.config_dir / "master_access.key"),
            ("special_user.json", auth_config.config_dir / "special_user.json"),
        ]
        
        existing_files = []
        for file_name, file_path in files_to_remove:
            if file_path.exists():
                existing_files.append((file_name, file_path))
                print(f"  - {file_name}")
        
        if not existing_files:
            print("削除する設定ファイルはありません。")
            return
        
        print()
        confirm = input("本当に削除しますか？ (y/N): ").lower()
        if confirm != 'y':
            print("キャンセルしました。")
            return
        
        removed_count = 0
        for file_name, file_path in existing_files:
            try:
                file_path.unlink()
                print(f"✅ {file_name} を削除しました")
                removed_count += 1
            except Exception as e:
                print(f"❌ {file_name} の削除に失敗: {e}")
        
        print()
        print(f"🎉 {removed_count}/{len(existing_files)} ファイルを削除しました。")
        print("💡 アプリケーションを再起動すると設定が反映されます。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン関数"""
    print("🔧 自動モザエセ 開発者モード・特定ユーザー設定ユーティリティ")
    print("=" * 60)
    
    while True:
        print("\n操作を選択してください:")
        print("1. 現在の状態確認")
        print("2. 開発者モード設定")
        print("3. 特定ユーザー設定作成")
        print("4. 開発者設定削除")
        print("5. 終了")
        
        choice = input("\n選択 (1-5): ").strip()
        
        if choice == "1":
            print("\n" + "=" * 60)
            check_current_status()
        
        elif choice == "2":
            print("\n" + "=" * 60)
            setup_developer_mode()
        
        elif choice == "3":
            print("\n" + "=" * 60)
            setup_special_user()
        
        elif choice == "4":
            print("\n" + "=" * 60)
            remove_developer_settings()
        
        elif choice == "5":
            print("\n👋 ユーティリティを終了します。")
            break
        
        else:
            print("❌ 無効な選択です。")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 ユーザーによって中断されました。")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc() 