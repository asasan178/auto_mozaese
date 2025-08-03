from auto_mosaic.src.encrypted_config import EncryptedConfigManager
from auto_mosaic.src.env_config import get_env_config

def migrate_discord_config():
    """環境変数からDiscord設定を読み込んで暗号化設定に移行"""
    
    print("=" * 60)
    print("🔄 Discord設定の移行 (.env → 暗号化設定)")
    print("=" * 60)
    
    # 環境変数から設定を読み込み
    try:
        env_config = get_env_config()
        
        # Discord設定を取得
        client_id = env_config.get_discord_client_id()
        client_secret = env_config.get_discord_client_secret()
        redirect_uri = env_config.get_discord_redirect_uri()
        scopes = env_config.get_discord_scopes()
        guild_configs = env_config.get_discord_guild_configs()
        max_failures = env_config.get_discord_max_consecutive_failures()
        cooldown = env_config.get_discord_role_check_cooldown()
        
        print(f"📋 環境変数から読み込んだDiscord設定:")
        print(f"  Client ID: {client_id or '未設定'}")
        print(f"  Client Secret: {'設定済み' if client_secret else '未設定'}")
        print(f"  Redirect URI: {redirect_uri}")
        print(f"  Scopes: {', '.join(scopes)}")
        print(f"  サーバー数: {len(guild_configs)}個")
        
        for i, guild in enumerate(guild_configs):
            print(f"    サーバー{i+1}: {guild.get('name', 'N/A')} (ID: {guild.get('guild_id', 'N/A')})")
            print(f"      必要ロール: {len(guild.get('required_roles', []))}個")
        
        # Discord設定の検証
        if not client_id or client_id == "demo_client_id":
            print("❌ 有効なDiscord Client IDが設定されていません")
            return False
            
        if not client_secret or client_secret == "demo_client_secret":
            print("❌ 有効なDiscord Client Secretが設定されていません")
            return False
        
        # 既存の暗号化設定を読み込み
        manager = EncryptedConfigManager()
        existing_config = manager.decrypt_config()
        if not existing_config:
            print("既存の設定が見つかりません。新しい設定を作成します。")
            existing_config = {}
        
        # Discord設定を構築
        discord_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "guilds": guild_configs,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "max_failures": max_failures,
            "cooldown": cooldown
        }
        
        # 既存設定にマージ
        existing_config.update(discord_config)
        
        # 暗号化して保存
        print("\n🔐 暗号化設定ファイルに保存中...")
        success = manager.encrypt_config(existing_config)
        
        if success:
            print("✅ Discord認証設定が正常に移行されました!")
            print("\n📍 次の手順:")
            print("1. exeファイルを再ビルドしてください")
            print("2. アプリケーションでDiscord認証を選択できるようになります")
            print("3. 認証URLは有効なClient IDを使用するようになります")
            
            return True
        else:
            print("❌ 暗号化設定の保存に失敗しました")
            return False
    
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        print(f"詳細: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    migrate_discord_config() 