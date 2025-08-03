from auto_mosaic.src.encrypted_config import EncryptedConfigManager

def check_discord_config():
    manager = EncryptedConfigManager()
    config = manager.decrypt_config()
    
    if config:
        print('現在の暗号化設定:')
        for key, value in config.items():
            if 'client' in key.lower():
                print(f'  {key}: {value}')
            elif 'guild' in key.lower():
                if isinstance(value, list):
                    print(f'  {key}: {len(value)}個のギルド')
                    for i, guild in enumerate(value):
                        if isinstance(guild, dict):
                            guild_id = guild.get('guild_id', 'N/A')
                            guild_name = guild.get('name', 'N/A') 
                            roles = guild.get('required_roles', [])
                            print(f'    Guild {i+1}: {guild_name} (ID: {guild_id}, ロール: {len(roles)}個)')
                else:
                    print(f'  {key}: {value}')
            else:
                print(f'  {key}: {value}')
    else:
        print('設定が見つからないか復号化に失敗しました')
        print('現在はデモ設定(demo_client_id)が使用されています')

if __name__ == "__main__":
    check_discord_config() 