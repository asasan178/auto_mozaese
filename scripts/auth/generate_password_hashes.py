#!/usr/bin/env python3
"""
パスワードハッシュ生成ユーティリティ
Auto Mosaic Tool用の.envファイル設定を支援

使用方法:
    python generate_password_hashes.py
"""

import hashlib
import getpass
import os
from pathlib import Path


def generate_hash(password: str) -> str:
    """パスワードのSHA256ハッシュを生成"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def generate_master_password():
    """マスターパスワードのハッシュを生成"""
    print("\n=== マスターパスワード設定 ===")
    print("管理者・開発者用のマスターパスワードを設定してください。")
    print("このパスワードは常時有効で、認証をバイパスできます。")
    
    while True:
        password = getpass.getpass("マスターパスワードを入力: ")
        if len(password) < 4:
            print("❌ パスワードは4文字以上で入力してください。")
            continue
        
        confirm = getpass.getpass("確認のため再度入力: ")
        if password != confirm:
            print("❌ パスワードが一致しません。")
            continue
        
        hash_value = generate_hash(password)
        print(f"✅ マスターパスワードハッシュ: {hash_value}")
        return hash_value


def generate_monthly_passwords():
    """月次パスワードのハッシュを生成"""
    print("\n=== 月次パスワード設定 ===")
    print("2025年の各月のパスワードを設定してください。")
    print("各パスワードは該当月のみ有効です。")
    
    monthly_hashes = {}
    
    for month in range(1, 13):
        month_name = f"2025年{month}月"
        
        while True:
            password = getpass.getpass(f"{month_name}のパスワードを入力: ")
            if len(password) < 4:
                print("❌ パスワードは4文字以上で入力してください。")
                continue
            
            hash_value = generate_hash(password)
            monthly_hashes[f"2025-{month:02d}"] = hash_value
            print(f"✅ {month_name}: {hash_value}")
            break
    
    return monthly_hashes


def create_env_file(master_hash: str, monthly_hashes: dict):
    """
    .envファイルを作成
    """
    env_content = f"""# ==================================================
# Auto Mosaic Tool - Environment Configuration
# ==================================================
# 自動生成されたファイル - 機密情報のため第三者と共有しないでください

# ==================================================
# 認証設定 (Authentication Settings)
# ==================================================

# マスターパスワードのSHA256ハッシュ（管理者・開発者用）
MASTER_PASSWORD_HASH={master_hash}

# 月次パスワード設定（YYYY-MM形式のキーとSHA256ハッシュ値）
"""
    
    # 月次パスワードを追加
    for month_key, hash_value in monthly_hashes.items():
        env_key = f"MONTHLY_PASSWORD_{month_key.replace('-', '_')}"
        env_content += f"{env_key}={hash_value}\n"
    
    env_content += """
# ==================================================
# 外部API設定 (External API Settings)
# ==================================================

# CivitAI API Key（オプション）
# CivitAIからモデルをダウンロードする際に使用
CIVITAI_API_KEY=

# ==================================================
# Discord OAuth設定 (Discord OAuth Settings) 
# ==================================================

# Discord OAuth2設定
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:8000/callback
DISCORD_SCOPES=identify,guilds,guilds.members.read

# Discord認証設定
DISCORD_MAX_CONSECUTIVE_FAILURES=3
DISCORD_ROLE_CHECK_COOLDOWN=10

# ==================================================
# Discord サーバー設定 (Discord Server Settings)
# ==================================================

# サーバー1（例）
DISCORD_GUILD_1_ID=your_guild_id_1
DISCORD_GUILD_1_NAME=Server Name 1
DISCORD_GUILD_1_ROLES=role_id_1,role_id_2

# サーバー2（例）
DISCORD_GUILD_2_ID=your_guild_id_2
DISCORD_GUILD_2_NAME=Server Name 2
DISCORD_GUILD_2_ROLES=role_id_1

# サーバー3（例）
DISCORD_GUILD_3_ID=your_guild_id_3
DISCORD_GUILD_3_NAME=Server Name 3
DISCORD_GUILD_3_ROLES=role_id_1,role_id_2

# サーバー4（例）
DISCORD_GUILD_4_ID=your_guild_id_4
DISCORD_GUILD_4_NAME=Server Name 4
DISCORD_GUILD_4_ROLES=role_id_1

# ==================================================
# 開発・デバッグ設定 (Development & Debug Settings)
# ==================================================

# デバッグモードを有効にする（true/false）
DEBUG_MODE=false

# 開発者モードを有効にする（true/false）
DEVELOPER_MODE=false

# ログレベル（DEBUG, INFO, WARNING, ERROR）
LOG_LEVEL=INFO

# ==================================================
# セキュリティ注意事項
# ==================================================
# - このファイルを第三者と共有しないでください
# - バージョン管理システム（Git等）にコミットしないでください
# - 適切なファイル権限を設定してください
# - パスワードを変更した場合は、このファイルを再生成してください
"""
    
    # .envファイルに書き込み
    env_path = Path(".env")
    
    # 既存ファイルがある場合は確認
    if env_path.exists():
        response = input("\n⚠️  .envファイルが既に存在します。上書きしますか？ (y/N): ")
        if response.lower() != 'y':
            print("❌ 操作をキャンセルしました。")
            return False
    
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # ファイル権限を制限（Unix系システムの場合）
        if os.name != 'nt':  # Windows以外
            env_path.chmod(0o600)  # オーナーのみ読み書き可能
        
        print(f"✅ .envファイルを作成しました: {env_path.absolute()}")
        return True
        
    except Exception as e:
        print(f"❌ .envファイルの作成に失敗しました: {e}")
        return False


def test_demo_passwords():
    """デモ用パスワードの確認"""
    print("\n=== デモ用パスワード参考 ===")
    print("開発・テスト用のデモパスワード:")
    print(f"マスター: 'demo' → {generate_hash('demo')}")
    
    for month in range(1, 13):
        demo_password = f"demo_2025_{month:02d}"
        hash_value = generate_hash(demo_password)
        print(f"2025-{month:02d}: '{demo_password}' → {hash_value}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Auto Mosaic Tool - パスワードハッシュ生成ユーティリティ")
    print("=" * 60)
    
    while True:
        print("\n選択してください:")
        print("1. 新規パスワード設定（推奨）")
        print("2. デモ用パスワード参考表示")
        print("3. 単一パスワードのハッシュ生成")
        print("0. 終了")
        
        choice = input("\n選択 (0-3): ").strip()
        
        if choice == '1':
            print("\n🔐 新規パスワード設定を開始します...")
            
            # マスターパスワード生成
            master_hash = generate_master_password()
            
            # 月次パスワード生成
            monthly_hashes = generate_monthly_passwords()
            
            # .envファイル作成
            print("\n📝 .envファイルを作成します...")
            if create_env_file(master_hash, monthly_hashes):
                print("\n🎉 設定完了！")
                print("生成された.envファイルを確認し、必要に応じてAPIキー等を追加してください。")
                break
            
        elif choice == '2':
            test_demo_passwords()
            
        elif choice == '3':
            password = getpass.getpass("\nパスワードを入力: ")
            if password:
                hash_value = generate_hash(password)
                print(f"ハッシュ値: {hash_value}")
            
        elif choice == '0':
            print("終了します。")
            break
            
        else:
            print("❌ 無効な選択です。")


if __name__ == "__main__":
    main() 