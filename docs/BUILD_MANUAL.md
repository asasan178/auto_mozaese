# 自動モザエセ - ビルドマニュアル v1.0

## 📋 概要

自動モザエセは、AI技術を活用した自動モザイク処理ツールです。このマニュアルでは、開発環境のセットアップからPyInstallerを使ったビルド、配布までの完全な手順を説明します。

### 🎯 対象読者
- プロジェクトの開発者・メンテナー
- ビルド・配布作業を行う担当者
- カスタムビルドを作成したい開発者

### 📦 ビルド成果物
- **配布版**: エンドユーザー向け（`自動モザエセ_配布版`）
- **開発者版**: 開発・デバッグ用（`自動モザエセ_開発版`）

### 🆕 v1.0での主要機能
- **PyInstallerベースビルド**: .specファイルによる標準的なビルドプロセス
- **バッチファイル依存排除**: クリーンで保守性の高いビルドシステム
- **統合認証システム**: 月次パスワード + Discord認証対応
- **カスタムモデル対応**: 任意の.ptファイルをカスタム検出器として使用可能
- **遅延ローダー**: exe化時のファイルサイズ削減とパフォーマンス向上
- **暗号化設定管理**: 配布版での認証情報安全管理
- **環境変数設定**: .envファイルによる柔軟な設定管理

---

## 🛠️ 前提条件

### 必要な環境
| 項目 | 要件 | 推奨 |
|------|------|------|
| **OS** | Windows 10/11 (64bit) | Windows 11 最新版 |
| **Python** | 3.11以上 | Python 3.11.9 |
| **メモリ** | 16GB以上 | 32GB以上 |
| **ストレージ** | 20GB以上の空き容量 | 50GB以上（SSD推奨） |
| **GPU** | CUDA対応GPU（オプション） | RTX 4060以上 |

### 必要なソフトウェア
```bash
# Python パッケージマネージャー
pip >= 23.0

# 仮想環境
venv (Pythonに含まれる)

# Git (ソース管理)
git >= 2.30

# 新規追加: 暗号化ライブラリ
# cryptography, python-dotenv
```

### v1.0機能対応の追加要件
- **暗号化設定作成**: 配布版用の認証情報設定
- **Discord OAuth2設定**: Discord認証用のクライアント設定
- **カスタムモデル**: 任意のYOLO形式.ptファイル
- **環境変数設定**: .envファイルによる開発者設定

---

## 🚀 クイックスタート（PyInstallerベース）

### 0. 事前準備（初回のみ）

```bash
# プロジェクトディレクトリに移動
cd auto_mosaic

# 仮想環境をアクティベート
.venv\Scripts\activate.bat

# CUDA/CPU環境に応じたONNXRuntime最適化（必須）
cd builds
python setup_onnx_runtime.py
```

⚠️ **重要**: `setup_onnx_runtime.py`は以下の処理を行います：
- CUDA環境検出とGPU版/CPU版ONNXRuntimeの自動選択
- 互換性のあるパッケージバージョン（NumPy 2.3.0等）の自動調整
- requirements.txtのONNXRuntimeバージョンを環境に応じて置換

### 1. 推奨ビルド方法

```bash
# プロジェクトディレクトリに移動
cd auto_mosaic

# 仮想環境をアクティベート
.venv\Scripts\activate.bat

# buildsディレクトリに移動
cd builds

# 配布版をビルド
pyinstaller build_distribution.spec --clean --noconfirm

# 開発者版をビルド
pyinstaller build_developer.spec --clean --noconfirm
```

### 2. ワンライナー実行

```bash
# 配布版のみ
cd builds && pyinstaller build_distribution.spec --clean --noconfirm

# 開発者版のみ
cd builds && pyinstaller build_developer.spec --clean --noconfirm

# 両方ビルド
cd builds && pyinstaller build_distribution.spec --clean --noconfirm && pyinstaller build_developer.spec --clean --noconfirm
```

### 3. ビルド結果

```
builds/
├── dist/                        # PyInstallerの出力ディレクトリ
│   ├── 自動モザエセ_配布版/       # 配布版
│   │   ├── 自動モザエセ.exe
│   │   ├── _internal/
│   │   ├── config/             # 暗号化設定
│   │   │   ├── auth.dat       # 暗号化認証情報
│   │   │   └── auth.salt      # 暗号化ソルト
│   │   └── models/            # 埋め込みモデル（オプション）
│   └── 自動モザエセ_開発版/       # 開発者版
│       ├── 自動モザエセ.exe
│       ├── .developer_mode     # 開発者モードマーカー
│       ├── .env               # 環境変数設定
│       └── _internal/
└── build/                      # PyInstallerの中間ファイル
    ├── 自動モザエセ_配布版/
    └── 自動モザエセ_開発版/
```

---

## 🔧 手動セットアップ

### 1. リポジトリの準備

```bash
# リポジトリをクローン（新規の場合）
git clone <repository-url> auto_mosaic
cd auto_mosaic

# 既存の場合は最新版に更新
git pull origin main
```

### 2. 仮想環境の作成

```bash
# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化
.venv\Scripts\activate.bat

# 依存関係をインストール（更新された要件）
pip install --upgrade pip
pip install -r requirements.txt

# 新規追加依存関係の確認
pip install cryptography python-dotenv
```

### 3. 環境設定ファイルの作成（v1.0機能）

#### .envファイルの作成
```bash
# プロジェクトルートに .env ファイルを作成
echo DEVELOPER_MODE=true > .env
echo MONTHLY_PASSWORD_2025_01=your_hashed_password >> .env
echo DISCORD_CLIENT_ID=your_discord_client_id >> .env
echo DISCORD_CLIENT_SECRET=your_discord_client_secret >> .env
```

**実際の.env例**:
```env
# 開発者モード設定
DEVELOPER_MODE=true

# 月次パスワード（ハッシュ値）
MONTHLY_PASSWORD_2025_01=8f4b5e2d7c9a1f6e3b8d4a7c2e9f1b5c8a3d6e9c2f5b8e1a4d7c0f3b6e9a2d5c8
MONTHLY_PASSWORD_2025_02=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b

# マスターパスワード（ハッシュ値）
MASTER_PASSWORD=master_password_hash_here

# Discord OAuth2設定
DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/callback
```

### 4. 開発環境の検証

```bash
# Python環境の確認
python --version

# 必要なライブラリの確認
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import ultralytics; print('YOLOv8: OK')"
python -c "import onnxruntime; print(f'ONNX Runtime: {onnxruntime.__version__}')"
python -c "import cryptography; print('暗号化ライブラリ: OK')"
python -c "import dotenv; print('環境変数ライブラリ: OK')"

# プロジェクトモジュールの確認
python -c "from auto_mosaic.src import gui; print('プロジェクトモジュール: OK')"

# v1.0機能の確認
python -c "from auto_mosaic.src.auth_manager import AuthenticationManager; print('統合認証: OK')"
python -c "from auto_mosaic.src.lazy_loader import LazyLoader; print('遅延ローダー: OK')"
```

---

## 🏗️ ビルドプロセス詳細

### 1. PyInstallerによるビルド

#### 配布版ビルド

```bash
# buildsディレクトリで実行
pyinstaller build_distribution.spec --clean --noconfirm
```

**build_distribution.specの主要設定**:
```python
# 配布版の特徴
console=False               # コンソールウィンドウなし（静音起動）
optimize=['O1']             # Pythonバイトコード最適化
strip=True                  # デバッグシンボル削除
upx=True                    # UPX圧縮有効

# データファイル
datas=[
    ('config/auth.dat', 'config/'),      # 暗号化設定
    ('config/auth.salt', 'config/'),     # 暗号化ソルト
    ('models/*.pt', 'models/'),          # カスタムモデル（オプション）
]

# 隠し依存関係
hiddenimports=[
    'cryptography.fernet',
    'auto_mosaic.src.auth_manager',
    'auto_mosaic.src.discord_auth_adapter',
    'auto_mosaic.src.encrypted_config',
    'auto_mosaic.src.lazy_loader',
]
```

#### 開発者版ビルド

```bash
# buildsディレクトリで実行
pyinstaller build_developer.spec --clean --noconfirm
```

**build_developer.specの主要設定**:
```python
# 開発者版の特徴
console=True                # コンソールウィンドウ表示
debug=True                  # デバッグ情報保持
optimize=[]                 # 最適化無効
strip=False                 # デバッグシンボル保持

# 開発者向けデータ
datas=[
    ('.env', '.'),                       # 環境変数設定
    ('.developer_mode', '.'),            # 開発者モードマーカー
    ('models/', 'models/'),              # モデルファイル全体
]
```

### 2. PyInstallerオプション説明

| オプション | 説明 |
|------------|------|
| `--clean` | 前回のビルドキャッシュを削除してクリーンビルド |
| `--noconfirm` | 出力ディレクトリの上書き確認を無効化 |
| `--onedir` | ディレクトリ形式で出力（デフォルト） |
| `--debug=all` | デバッグモード（トラブルシューティング時） |

---

## 📁 ビルド構成ファイル

### .specファイル（PyInstaller設定）

| ファイル | 用途 | 特徴 |
|----------|------|------|
| `builds/build_distribution.spec` | 配布版ビルド設定 | 暗号化設定埋め込み、遅延ローダー、静音起動 |
| `builds/build_developer.spec` | 開発者版ビルド設定 | .env対応、コンソール出力、デバッグ機能 |

### サポートスクリプト

| スクリプト | 機能 | 用途 |
|------------|------|------|
| `builds/runtime_hook_onnx.py` | ONNXランタイムフック | DLL読み込み最適化 |
| `builds/runtime_hook_onnx_distribution.py` | 配布版ONNXフック | 配布版専用最適化 |
| `builds/setup_onnx_runtime.py` | ONNX Runtime設定 | CUDA/CPU自動選択 |
| `setup_encrypted_config.py` | 暗号化設定作成 | 配布版認証情報管理 |
| `setup_env_config.py` | 環境変数検証 | .env設定確認 |

### 不要になったファイル（削除対象）

以下のバッチファイルは新しいビルドシステムでは不要です：

| 削除対象 | 理由 |
|----------|------|
| `build_*.bat` | PyInstallerの直接実行に置き換え |
| `builds/*.bat` | .specファイルベースのビルドに移行 |
| `start_*.bat` | 必要に応じて個別に作成 |

---

## 🔐 v1.0機能対応セットアップ

### 1. 暗号化設定の作成

```bash
# 配布版用暗号化設定を作成
python setup_encrypted_config.py

# または手動作成
python -c "
from auto_mosaic.src.encrypted_config import EncryptedConfigManager
config_manager = EncryptedConfigManager()
config_manager.create_encrypted_config({
    'monthly_passwords': {
        '2025-01': 'hashed_password_1',
        '2025-02': 'hashed_password_2'
    },
    'discord_config': {
        'client_id': 'your_client_id',
        'client_secret': 'your_client_secret'
    }
})
"
```

### 2. カスタムモデル対応

```bash
# カスタムモデルフォルダを作成
mkdir custom_models

# カスタムモデルを配置
# custom_models/my_anime_model.pt
# custom_models/my_detection_model.pt

# ビルド時にカスタムモデルを含める場合
# build_distribution.spec に追加:
# datas=[('custom_models/*.pt', 'custom_models/')]
```

### 3. Discord認証設定

```bash
# Discord Developer Portalでアプリケーション作成
# 1. https://discord.com/developers/applications にアクセス
# 2. 新しいアプリケーションを作成
# 3. OAuth2 > Redirects に http://localhost:8000/callback を追加
# 4. Bot > Privileged Gateway Intents を設定

# .envファイルに設定追加
echo DISCORD_CLIENT_ID=your_actual_client_id >> .env
echo DISCORD_CLIENT_SECRET=your_actual_client_secret >> .env
```

---

## 🔍 環境診断とトラブルシューティング

### 環境診断の実行

```bash
# PyInstallerバージョン確認
pyinstaller --version

# Python環境確認
python -c "
import sys
print(f'Python: {sys.version}')
print(f'Platform: {sys.platform}')
"

# プロジェクト固有の確認
python -c "
from auto_mosaic.src.utils import get_device_info
from auto_mosaic.src.env_config import get_env_config
from auto_mosaic.src.auth_config import AuthConfig

print('=== システム診断 ===')
print(f'デバイス情報: {get_device_info()}')

env_config = get_env_config()
print(f'開発者モード: {env_config.is_developer_mode()}')

auth_config = AuthConfig()
print(f'認証方式切り替え可能: {auth_config.is_auth_method_switching_available()}')
"

# .specファイル存在確認
cd builds
dir *.spec
```

### よくある問題と解決方法

#### 1. PyInstallerエラー

**エラー**: `pyinstaller: command not found`
```bash
# 解決方法
pip install pyinstaller
```

**エラー**: `ModuleNotFoundError: No module named 'cryptography'`
```bash
# 解決方法
pip install cryptography python-dotenv
```

**エラー**: `.spec file not found`
```bash
# 解決方法: buildsディレクトリに移動
cd builds
pyinstaller build_distribution.spec --clean --noconfirm
```

#### 2. 環境変数設定エラー

**エラー**: `.env file not found or invalid`
```

**解決方法:**
```bash
# .envファイル作成
echo DEVELOPER_MODE=true > .env

# 権限確認
ls -la .env
```

#### 3. 暗号化設定エラー

```bash
[ERROR] Encrypted config decryption failed
```

**解決方法:**
```bash
# 暗号化設定を再作成
python setup_encrypted_config.py --reset

# または手動削除して再作成
del config\auth.dat config\auth.salt
```

#### 4. カスタムモデル読み込みエラー

```bash
[ERROR] Custom model file not found
```

**解決方法:**
```bash
# カスタムモデルパス確認
python -c "
from pathlib import Path
model_path = Path('custom_models/my_model.pt')
print(f'モデル存在: {model_path.exists()}')
print(f'絶対パス: {model_path.absolute()}')
"
```

#### 5. Discord認証エラー

```bash
[ERROR] Discord authentication failed: Invalid client credentials
```

**解決方法:**
```bash
# Discord設定確認
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Client ID: {os.getenv(\"DISCORD_CLIENT_ID\", \"未設定\")}')
print(f'Client Secret: {\"設定済み\" if os.getenv(\"DISCORD_CLIENT_SECRET\") else \"未設定\"}')
"
```

---

## 📊 ビルド最適化設定（更新）

### サイズ最適化（新機能対応）

```python
# PyInstallerオプション
excludes=[
    'tkinter.test',
    'test',
    'unittest',
    'distutils',
    'setuptools',
    # 新規追加: 未使用認証モジュール
    'oauth2lib',          # Discord認証未使用時
    'cryptography.hazmat.backends.openssl.rsa',  # 未使用暗号化機能
]

# UPX圧縮設定（更新）
upx=True
upx_exclude=[
    'vcruntime140.dll',
    'msvcp140.dll',
    'api-*.dll',
    # 新規追加: CUDA DLL
    'cudart64_*.dll',
    'cublas64_*.dll',
    'cufft64_*.dll',
]
```

### パフォーマンス最適化（遅延ローダー対応）

```python
# Python最適化
optimize=['O1']

# 遅延ローダー対応ファイル配置
datas=[
    ('models/*.onnx', 'models/'),
    ('config/auth.dat', 'config/'),
    # CUDA DLLを分離配置
    ('cuda_libs/*.dll', 'cuda_libs/'),
    ('external_libs/*.dll', 'external_libs/'),
]

# 遅延インポート設定
hiddenimports=[
    'auto_mosaic.src.lazy_loader',
    'torch',                    # 遅延ロード対象
    'ultralytics',             # 遅延ロード対象
    'segment_anything',        # 遅延ロード対象
]
```

---

## 🎁 配布パッケージ作成（更新）

### 配布用ZIP作成

```bash
# 配布版パッケージ作成（設定ファイル含む）
cd dist
powershell Compress-Archive -Path "自動モザエセ_配布版" -DestinationPath "自動モザエセ_v1.2_配布版.zip"

# 開発者版パッケージ作成（.env含む）
powershell Compress-Archive -Path "自動モザエセ_開発版" -DestinationPath "自動モザエセ_v1.2_開発版.zip"

# カスタムモデル対応版作成
powershell Compress-Archive -Path "自動モザエセ_配布版", "custom_models" -DestinationPath "自動モザエセ_v1.2_カスタムモデル対応版.zip"
```

### 配布用README作成（更新）

```markdown
# 自動モザエセ v1.2

## インストール方法
1. ZIPファイルを任意の場所に展開
2. `自動モザエセ.exe`をダブルクリックして起動

## システム要件
- Windows 10/11 (64bit)
- メモリ: 16GB以上推奨
- ストレージ: 10GB以上の空き容量

## 🆕 v1.2の新機能
- **統合認証システム**: 月次パスワード + Discord認証
- **カスタムモデル対応**: 任意の.ptファイルを検出器として使用可能
- **高速化**: 遅延ローダーによる起動時間短縮

## 初回起動時
- 初回セットアップダイアログが表示されます
- モデルファイルの自動ダウンロードが開始されます（ネットワーク接続必要）
- Discord認証を使用する場合はブラウザが開きます

## カスタムモデルの使用方法
1. 設定 > 高度なオプション > カスタムモデル設定
2. 「カスタムモデルを使用する」にチェック
3. 「モデル追加」で.ptファイルを選択
4. クラスマッピングを設定（オプション）

## トラブルシューティング
- 起動しない場合: Windows Defenderの除外設定を確認
- Discord認証に失敗する場合: ブラウザのポップアップブロックを無効化
- カスタムモデルが読み込まれない場合: ファイルパスと.ptファイル形式を確認
```

---

## 🔄 継続的ビルド（CI/CD）

### 自動ビルドスクリプト（PowerShell）

```powershell
# auto_build.ps1
Write-Host "=== 自動モザエセ 自動ビルドシステム v1.0 ===" -ForegroundColor Green

# 仮想環境をアクティベート
& .venv\Scripts\Activate.ps1

Write-Host "[1/5] 環境変数設定確認..." -ForegroundColor Yellow
python setup_env_config.py --verify

Write-Host "[2/5] 暗号化設定確認..." -ForegroundColor Yellow
python setup_encrypted_config.py --verify

Write-Host "[3/5] 配布版ビルド..." -ForegroundColor Yellow
Set-Location builds
pyinstaller build_distribution.spec --clean --noconfirm

Write-Host "[4/5] 開発者版ビルド..." -ForegroundColor Yellow
pyinstaller build_developer.spec --clean --noconfirm

Write-Host "[5/5] パッケージ作成..." -ForegroundColor Yellow
Set-Location dist
Compress-Archive -Path "自動モザエセ_配布版" -DestinationPath "../release/auto_mosaic_distribution.zip" -Force
Compress-Archive -Path "自動モザエセ_開発版" -DestinationPath "../release/auto_mosaic_developer.zip" -Force
Set-Location ..

Write-Host "ビルド完了！" -ForegroundColor Green
```

### GitHub Actionsワークフロー例

```yaml
# .github/workflows/build.yml
name: Build Auto Mosaic

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build application
      run: |
        cd builds
        pyinstaller build_distribution.spec --clean --noconfirm
        pyinstaller build_developer.spec --clean --noconfirm

    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: auto-mosaic-builds
        path: builds/dist/
```

### 自動テストスクリプト

```python
# test_build_integrity.py
import subprocess
import sys
from pathlib import Path
import os

def test_exe_startup():
    """EXEファイルの起動テスト"""
    exe_path = Path("builds/dist/自動モザエセ_配布版/自動モザエセ.exe")
    if not exe_path.exists():
        return False, "EXE file not found"
    
    # 3秒間の起動テスト
    try:
        result = subprocess.run([str(exe_path), "--test"], 
                              timeout=3, capture_output=True)
        return result.returncode == 0, "Startup test"
    except subprocess.TimeoutExpired:
        return True, "Startup test (timeout OK)"

def test_spec_files():
    """Specファイルの存在確認"""
    spec_files = [
        Path("builds/build_distribution.spec"),
        Path("builds/build_developer.spec")
    ]
    
    missing = [f for f in spec_files if not f.exists()]
    if missing:
        return False, f"Missing spec files: {missing}"
    return True, "All spec files found"

def test_pyinstaller_available():
    """PyInstallerの可用性テスト"""
    try:
        result = subprocess.run(["pyinstaller", "--version"], 
                              capture_output=True, text=True)
        return result.returncode == 0, f"PyInstaller {result.stdout.strip()}"
    except FileNotFoundError:
        return False, "PyInstaller not found"

def test_auth_system():
    """認証システムのテスト"""
    try:
        from auto_mosaic.src.auth_manager import AuthenticationManager
        auth_manager = AuthenticationManager()
        return True, "Auth system OK"
    except Exception as e:
        return False, f"Auth system error: {e}"

def test_lazy_loader():
    """遅延ローダーのテスト"""
    try:
        from auto_mosaic.src.lazy_loader import LazyLoader
        loader = LazyLoader()
        return True, "Lazy loader OK"
    except Exception as e:
        return False, f"Lazy loader error: {e}"

if __name__ == "__main__":
    tests = [
        ("PyInstaller可用性", test_pyinstaller_available),
        (".specファイル", test_spec_files),
        ("EXE起動", test_exe_startup),
        ("認証システム", test_auth_system),
        ("遅延ローダー", test_lazy_loader),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        success, message = test_func()
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n✅ 全てのビルド検証に成功しました")
        sys.exit(0)
    else:
        print("\n❌ ビルド検証に失敗しました")
        sys.exit(1)
```

---

## 📈 バージョン管理（更新）

### バージョン番号規則

```
v[メジャー].[マイナー].[パッチ][-プレリリース]

例:
v1.0.0     - 初回リリース（統合認証、カスタムモデル対応）
v1.0.1     - バグフィックス
v1.0.2     - セキュリティ更新
v1.1.0-rc1 - 次期バージョンのリリース候補
```

### タグ付きビルド

```bash
# バージョンタグを作成
git tag -a v1.0.0 -m "Release version 1.0.0 - PyInstallerベースビルドシステム"
git push origin v1.0.0

# タグ付きビルド実行
git checkout v1.0.0

# 環境設定を確認してからビルド
python setup_env_config.py --verify

# PyInstallerでビルド
cd builds
pyinstaller build_distribution.spec --clean --noconfirm
pyinstaller build_developer.spec --clean --noconfirm
```

---

## 📚 参考資料

### 公式ドキュメント
- [PyInstaller公式ドキュメント](https://pyinstaller.readthedocs.io/)
- [PyInstaller .spec ファイル](https://pyinstaller.readthedocs.io/en/stable/spec-files.html)
- [PyTorch配布ガイド](https://pytorch.org/tutorials/advanced/cpp_export.html)
- [ONNX Runtime配布](https://onnxruntime.ai/docs/install/)
- [Cryptography配布ガイド](https://cryptography.io/en/latest/installation/)
- [Discord OAuth2ドキュメント](https://discord.com/developers/docs/topics/oauth2)

### プロジェクト関連ドキュメント
- `docs/API_Documentation.md` - 統合認証・カスタムモデル対応APIリファレンス
- `docs/DEVELOPER_GUIDE.md` - 開発者向けガイド
- `docs/USER_GUIDE.md` - エンドユーザー向けガイド
- `docs/CODE_ARCHITECTURE.md` - アーキテクチャドキュメント

---

## 🆘 サポート・問い合わせ

### ビルド失敗時の情報収集

```bash
# 環境情報収集
python --version > build_environment_v1.0.txt
pip list >> build_environment_v1.0.txt
echo %PATH% >> build_environment_v1.0.txt

# PyInstaller情報
pyinstaller --version >> build_environment_v1.0.txt

# v1.0機能確認
python -c "import cryptography; print(f'cryptography: {cryptography.__version__}')" >> build_environment_v1.0.txt
python -c "import dotenv; print('python-dotenv: OK')" >> build_environment_v1.0.txt

# 設定ファイル確認
dir .env >> build_environment_v1.0.txt
dir config\auth.dat >> build_environment_v1.0.txt
dir builds\*.spec >> build_environment_v1.0.txt

# PyInstallerビルドログ収集
copy builds\build\*\warn-*.txt build_logs_v1.0\
```

### PyInstallerデバッグモード

```bash
# 詳細デバッグモードでビルド
cd builds
pyinstaller build_distribution.spec --clean --noconfirm --debug=all

# または個別ログ出力
pyinstaller build_distribution.spec --clean --noconfirm --log-level=DEBUG
```

### トラブルシューティングコマンド

```bash
# 統合認証システムテスト
python -c "
from auto_mosaic.src.auth_manager import AuthenticationManager
auth_manager = AuthenticationManager()
print(f'現在の認証方式: {auth_manager.get_current_auth_method()}')
print(f'認証状態: {auth_manager.is_authenticated()}')
"

# 遅延ローダーテスト
python -c "
from auto_mosaic.src.lazy_loader import LazyLoader
loader = LazyLoader()
torch = loader.load_module('torch')
print(f'遅延ローダー経由でPyTorch読み込み: {torch.__version__}')
"

# ビルド完全性チェック
python test_build_integrity.py
```

---

**📝 このマニュアルは自動モザエセ v1.0対応です。**
**🔄 最終更新: 2025年8月**
**🔧 主要機能: PyInstallerベースビルド、統合認証システム、カスタムモデル対応、遅延ローダー** 