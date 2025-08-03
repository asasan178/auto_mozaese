from auto_mosaic.src.encrypted_config import EncryptedConfigManager

def update_discord_config():
    """Discord認証設定を暗号化設定ファイルに追加"""
    
    manager = EncryptedConfigManager()
    
    # 既存の設定を読み込み
    existing_config = manager.decrypt_config()
    if not existing_config:
        print("既存の設定が見つかりません。新しい設定を作成します。")
        existing_config = {}
    
    # Discord認証設定を追加
    # 注意: 実際のClient IDとSecretを設定する必要があります
    discord_config = {
        "client_id": "YOUR_ACTUAL_DISCORD_CLIENT_ID",  # 実際のDiscord Client IDに置き換えてください
        "client_secret": "YOUR_ACTUAL_DISCORD_CLIENT_SECRET",  # 実際のDiscord Client Secretに置き換えてください
        "guilds": [
            {
                "guild_id": "YOUR_DISCORD_SERVER_ID",  # 実際のDiscordサーバーIDに置き換えてください
                "name": "認証用サーバー",
                "required_roles": ["ROLE_ID_1", "ROLE_ID_2"]  # 実際のロールIDに置き換えてください
            }
        ],
        "redirect_uri": "http://localhost:8000/callback",
        "scopes": ["identify", "guilds", "guilds.members.read"],
        "max_failures": 3,
        "cooldown": 10
    }
    
    # 既存の設定にDiscord認証設定をマージ
    existing_config.update(discord_config)
    
    print("=" * 50)
    print("Discord認証設定の追加")
    print("=" * 50)
    print("\n⚠️  重要: このスクリプトを実行する前に、以下の情報を実際の値に置き換えてください:")
    print("1. YOUR_ACTUAL_DISCORD_CLIENT_ID")
    print("2. YOUR_ACTUAL_DISCORD_CLIENT_SECRET") 
    print("3. YOUR_DISCORD_SERVER_ID")
    print("4. ROLE_ID_1, ROLE_ID_2 (必要なロールID)")
    print("\nこれらの情報はDiscord Developer Portal (https://discord.com/developers/applications) で取得できます。")
    print("\n現在の設定にデモ値が含まれています。実際の値に更新してから再実行してください。")
    
    # デモ値のチェック
    if discord_config["client_id"] == "YOUR_ACTUAL_DISCORD_CLIENT_ID":
        print("\n❌ エラー: デモ値が設定されています。実際のDiscord認証情報に置き換えてください。")
        return False
    
    # 設定を暗号化して保存
    success = manager.encrypt_config(existing_config)
    
    if success:
        print("✅ Discord認証設定が正常に追加されました。")
        print("次回のアプリケーション実行時からDiscord認証が利用可能になります。")
        return True
    else:
        print("❌ 設定の保存に失敗しました。")
        return False

if __name__ == "__main__":
    update_discord_config() 