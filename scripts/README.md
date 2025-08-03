# スクリプトディレクトリ

このディレクトリには、自動モザエセの開発・設定・メンテナンス用スクリプトが含まれています。

## 📁 ディレクトリ構成

### `setup/` - セットアップ関連
- `setup_developer_mode.py` - 開発者モードの設定
- `create_distribution_config.py` - 配布用設定の作成
- `migrate_env_to_encrypted.py` - 環境変数から暗号化設定への移行

### `auth/` - 認証関連
- `generate_password_hashes.py` - パスワードハッシュの生成
- `update_discord_config.py` - Discord設定の更新
- `check_discord_config.py` - Discord設定の確認
- `test_discord_config.py` - Discord認証のテスト

### `models/` - モデル関連
- `download_correct_nudenet_from_hf.py` - Hugging FaceからNudeNetモデルをダウンロード
- `force_nudenet_download.py` - NudeNetモデルの強制ダウンロード
- `download_correct_nudenet_models.py` - 正しいNudeNetモデルのダウンロード
- `extract_nudenet_models.py` - NudeNetモデルの展開

## 🚀 使用方法

### 開発環境セットアップ
```bash
# 開発者モードの設定
python scripts/setup/setup_developer_mode.py

# 暗号化設定の作成
python scripts/setup/create_distribution_config.py
```

### 認証システム設定
```bash
# パスワードハッシュの生成
python scripts/auth/generate_password_hashes.py

# Discord設定の確認
python scripts/auth/check_discord_config.py
```

### モデル管理
```bash
# NudeNetモデルのダウンロード
python scripts/models/download_correct_nudenet_models.py

# モデルファイルの展開
python scripts/models/extract_nudenet_models.py
```

## ⚠️ 注意事項

- これらのスクリプトは主に開発・メンテナンス用です
- 一般ユーザーは通常これらのスクリプトを直接実行する必要はありません
- 認証関連スクリプトを実行する際は、機密情報の取り扱いに注意してください