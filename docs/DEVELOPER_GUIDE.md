# 🎯 自動モザエセ v1.0 - 開発者ガイド

## 📋 概要

このドキュメントは、自動モザエセ v1.0の開発・保守・拡張・カスタマイズに関する技術的な詳細情報を提供します。エンドユーザー向けの情報は`USER_GUIDE.md`をご参照ください。

### 🎯 対象読者
- プロジェクトの開発者・メンテナー
- 技術的なカスタマイズを行いたい上級ユーザー
- AIモデルの研究・開発者
- 企業での導入・運用担当者

---

## 🏗️ システム要件・技術仕様

### 最小システム要件
| 項目 | 最小要件 | 推奨要件 |
|------|----------|----------|
| **OS** | Windows 10 (64bit) | Windows 11 最新版 |
| **CPU** | Intel i5-8400 / AMD Ryzen 5 2600 | Intel i7-10700K / AMD Ryzen 7 3700X |
| **メモリ** | 16GB | 32GB以上 |
| **GPU** | なし（CPU処理可能） | NVIDIA RTX 4060以上（CUDA対応） |
| **ストレージ** | 20GB以上の空き容量 | 50GB以上（SSD推奨） |
| **ネットワーク** | インターネット接続（認証・セットアップ） | 高速ブロードバンド |

### 技術スタック
```
🔧 コア技術:
- Python 3.11+
- PyTorch 2.7.1+
- CUDA 12.8（GPU使用時）
- OpenCV 4.8+
- NumPy 2.3.0

🧠 AI技術:
- YOLOv8 (Ultralytics) - 物体検出
- SAM ViT-B (Meta AI) - セグメンテーション
- NudeNet - 実写画像対応
- カスタムモデル（YOLO形式.pt）

🎨 UI・認証:
- tkinter - デスクトップGUI
- Discord OAuth2 - 認証システム
- 暗号化設定管理

📦 パッケージング:
- PyInstaller 6.14.2+ - 実行可能ファイル生成
- 遅延ローダー - 起動高速化
```

---

## 🚀 開発環境セットアップ

### 1. Python環境構築
```bash
# Python 3.11のインストール確認
python --version  # 3.11.9+

# 仮想環境作成
python -m venv .venv

# 仮想環境有効化
# Windows:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

### 2. 依存関係インストール
```bash
# 基本依存関係
pip install -r requirements.txt

# 開発用依存関係
pip install -r requirements-dev.txt

# GPU対応（NVIDIA環境）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### 3. 必要なAIモデルファイルの配置

#### 3.1 Anime NSFW Detection v4.0
```bash
# ダウンロード先: https://civitai.com/models/1313556?modelVersionId=1863248
# ファイル: animeNSFWDetection_v40.zip

# 展開後、以下のファイルを配置:
models/animeNSFWDetection_v40.pt
```

#### 3.2 SAM ViT-B
```bash
# ダウンロード先: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
# ファイル: sam_vit_b_01ec64.pth

# 配置場所:
models/sam_vit_b_01ec64.pth
```

#### 3.3 NudeNet（実写画像対応）
```bash
# 以下のファイルをnudenet_modelsフォルダに配置:
nudenet_models/detector_v2_default_checkpoint.onnx
nudenet_models/classifier_model.onnx
nudenet_models/320n.onnx
```

### 4. 環境変数設定（開発者モード）
```bash
# .envファイルを作成
AUTO_MOSAIC_DEV_MODE=true
DEVELOPER_MODE=true

# Discord OAuth2設定（開発用）
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_REDIRECT_URI=http://localhost:8080/callback
```

---

## 🔧 高度な設定・カスタマイズ

### カスタムモデル対応

#### 対応形式
```python
# YOLOv8形式のモデル（.pt）のみサポート
supported_formats = ['.pt']

# クラスマッピング例
class_mapping = {
    0: 'penis',
    1: 'labia_minora', 
    2: 'labia_majora',
    3: 'testicles',
    4: 'anus',
    5: 'nipples',
    6: 'xray',
    7: 'cross_section'
}
```

#### カスタムモデル追加手順
```python
# 1. モデルファイルの配置
custom_models/your_model.pt

# 2. 設定ファイルでの登録
{
    "your_model": {
        "path": "custom_models/your_model.pt",
        "class_mapping": {...},
        "enabled": true,
        "confidence_threshold": 0.25
    }
}
```

### 検出精度チューニング

#### パラメータ調整
```python
# 信頼度閾値（検出感度）
confidence_threshold: float = 0.25  # 0.1-0.9

# NMS（Non-Maximum Suppression）閾値
nms_threshold: float = 0.45  # 0.1-0.9

# バウンディングボックス拡張
bbox_expansion: int = 15  # -50 to +100 pixels

# 個別拡張設定
individual_expansion = {
    'penis': 15,
    'labia_minora': 10,
    'labia_majora': 15,
    'testicles': 20,
    'anus': 15,
    'nipples': 10
}
```

#### セグメンテーション設定
```python
# SAM ViT-B設定
sam_config = {
    'model_type': 'vit_b',
    'checkpoint': 'models/sam_vit_b_01ec64.pth',
    'device': 'cuda',  # 'cpu' or 'cuda'
    'points_per_side': 32,
    'pred_iou_thresh': 0.88,
    'stability_score_thresh': 0.95
}
```

### 処理パフォーマンス最適化

#### GPU最適化
```python
# CUDA設定
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cudnn.benchmark = True

# メモリ効率化
torch.cuda.empty_cache()  # 定期的なキャッシュクリア
```

#### 遅延ローダー設定
```python
# 遅延ローダー対象モジュール
lazy_modules = [
    'torch',
    'torchvision', 
    'ultralytics',
    'cv2',
    'numpy',
    'PIL',
    'segment_anything',
    'nudenet'
]

# 起動時間短縮: 2-3倍高速化
# メモリ使用量削減: 20-30%
```

---

## 🔐 認証システム詳細

### Discord OAuth2実装

#### 認証フロー
```python
# 1. 認証URL生成
auth_url = f"https://discord.com/api/oauth2/authorize?" \
           f"client_id={CLIENT_ID}&" \
           f"redirect_uri={REDIRECT_URI}&" \
           f"response_type=code&" \
           f"scope=identify+guilds.members.read"

# 2. トークン取得
token_response = requests.post(
    "https://discord.com/api/oauth2/token",
    data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
)

# 3. ユーザー情報取得・ロール確認
user_info = requests.get(
    "https://discord.com/api/users/@me",
    headers={'Authorization': f'Bearer {access_token}'}
)
```

#### 暗号化設定管理
```python
# 認証情報の暗号化保存
from cryptography.fernet import Fernet

# 暗号化キー生成・保存
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# データ暗号化
encrypted_data = cipher_suite.encrypt(auth_data.encode())

# 安全な保存場所
config_path = get_app_data_dir() / "config" / "auth.dat"
```

---

## 🔍 診断・デバッグ機能

### ログシステム

#### ログレベル設定
```python
# 開発者モード: DEBUGレベル
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 本番モード: INFOレベル
logging.basicConfig(level=logging.INFO)
```

#### ログファイル構成
```
logs/
├── auto_mosaic.log        # メインアプリケーションログ
├── auth.log              # 認証関連ログ
├── detector.log          # AI検出ログ
├── performance.log       # パフォーマンス監視ログ
└── error.log            # エラー専用ログ
```

### パフォーマンス監視

#### メトリクス収集
```python
# 処理時間測定
import time
start_time = time.time()
# ... 処理 ...
processing_time = time.time() - start_time

# メモリ使用量監視
import psutil
memory_usage = psutil.virtual_memory().percent
gpu_memory = torch.cuda.memory_allocated() / 1024**3  # GB

# GPU使用率監視
import nvidia_ml_py as nvml
nvml.nvmlInit()
handle = nvml.nvmlDeviceGetHandleByIndex(0)
utilization = nvml.nvmlDeviceGetUtilizationRates(handle)
```

### デバッグ用可視化

#### 検出結果可視化
```python
# バウンディングボックス描画
def visualize_detections(image, bboxes, labels, confidences):
    for bbox, label, conf in zip(bboxes, labels, confidences):
        x1, y1, x2, y2 = bbox
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, f'{label}: {conf:.2f}', 
                   (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return image

# セグメンテーション結果表示
def visualize_masks(image, masks):
    overlay = image.copy()
    for mask in masks:
        overlay[mask > 0] = [0, 255, 0]  # Green overlay
    result = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
    return result
```

---

## 📦 ビルド・配布

### PyInstallerビルド設定

#### 開発者版ビルド
```bash
# builds/build_developer.bat
pyinstaller build_developer.spec --clean --noconfirm
```

#### 配布版ビルド
```bash
# builds/build_distribution.bat
set AUTO_MOSAIC_DEV_MODE=false
set DEVELOPER_MODE=false
pyinstaller build_distribution.spec --clean --noconfirm
```

#### Specファイル重要設定
```python
# onnxruntime対応
hiddenimports=[
    'onnxruntime',
    'onnxruntime.capi', 
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'nudenet',
    'nudenet.classifier',
    'nudenet.detector'
]

# DLLファイル包含
binaries=[
    ('C:\\Windows\\System32\\msvcp140.dll', '.'),
    ('C:\\Windows\\System32\\vcruntime140.dll', '.'),
    ('C:\\Windows\\System32\\vcruntime140_1.dll', '.'),
] + collect_dynamic_libs('onnxruntime')

# データファイル包含
datas=[
    ('../nudenet_models/detector_v2_default_checkpoint.onnx', '.'),
    ('../nudenet_models/classifier_model.onnx', '.'),
    ('../nudenet_models/320n.onnx', '.'),
    # ... 他のファイル
]
```

### 配布パッケージ最適化

#### ファイルサイズ削減
```python
# 不要ファイル除外
excludes = [
    'matplotlib.tests',
    'numpy.tests',
    'PIL.tests',
    'torch.test',
    'torchvision.datasets'
]

# アップデート用差分パッケージ
def create_delta_package(old_version, new_version):
    # バイナリ差分生成
    # 増分アップデート対応
    pass
```

---

## 🧪 テスト・品質保証

### 単体テスト

#### テスト構成
```python
# tests/test_detector.py
def test_anime_detection():
    detector = create_detector('anime')
    image = cv2.imread('test_images/anime_sample.jpg')
    results = detector.detect(image)
    assert len(results) > 0
    assert results[0]['confidence'] > 0.5

# tests/test_segmenter.py  
def test_sam_segmentation():
    segmenter = create_segmenter('sam_vit_b')
    image = cv2.imread('test_images/test_sample.jpg')
    bboxes = [(100, 100, 200, 200)]
    masks = segmenter.segment(image, bboxes)
    assert len(masks) == len(bboxes)
```

#### パフォーマンステスト
```python
def test_processing_speed():
    # 1000枚画像での処理速度テスト
    start_time = time.time()
    process_batch(test_images[:1000])
    total_time = time.time() - start_time
    avg_time = total_time / 1000
    assert avg_time < 2.0  # 2秒/枚以内
```

### 統合テスト

#### エンドツーエンドテスト
```python
def test_full_pipeline():
    # 1. 画像読み込み
    # 2. AI検出
    # 3. セグメンテーション  
    # 4. モザイク適用
    # 5. ファイル保存
    # 6. 結果検証
    pass
```

### 品質メトリクス

#### 検出精度評価
```python
# Precision, Recall, F1-Score計算
def evaluate_detection_accuracy(ground_truth, predictions):
    tp = count_true_positives(ground_truth, predictions)
    fp = count_false_positives(ground_truth, predictions) 
    fn = count_false_negatives(ground_truth, predictions)
    
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1_score = 2 * (precision * recall) / (precision + recall)
    
    return precision, recall, f1_score
```

---

## 🚨 トラブルシューティング

### よくある技術的問題

#### 1. ONNXRuntime関連エラー
```python
# エラー: DLL load failed while importing onnxruntime_pybind11_state
# 解決策:
# 1. Visual C++ Redistributable 2019-2022の確認
# 2. ONNXRuntimeのバージョン確認
# 3. CUDA/CUDNNのバージョン互換性確認

# デバッグ用コード
try:
    import onnxruntime as ort
    print(f"ONNXRuntime version: {ort.__version__}")
    print(f"Available providers: {ort.get_available_providers()}")
except Exception as e:
    print(f"ONNXRuntime import error: {e}")
```

#### 2. GPU認識問題
```python
# CUDA利用可能性確認
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name()}")
```

#### 3. メモリ不足対策
```python
# メモリ使用量監視
def monitor_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        cached = torch.cuda.memory_reserved() / 1024**3
        print(f"GPU Memory - Allocated: {allocated:.2f}GB, Cached: {cached:.2f}GB")
    
    import psutil
    ram_usage = psutil.virtual_memory().percent
    print(f"RAM Usage: {ram_usage:.1f}%")

# メモリクリア
def clear_memory():
    torch.cuda.empty_cache()
    import gc
    gc.collect()
```

### パフォーマンス問題診断

#### プロファイリング
```python
# 処理時間プロファイリング
import cProfile
import pstats

def profile_processing():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 処理実行
    process_images(test_images)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # 上位20関数
```

---

## 🔮 将来の拡張・ロードマップ

### 予定機能

#### 短期（v1.1-1.2）
- [ ] バッチ処理のUI改善
- [ ] カスタムモデル管理の強化
- [ ] パフォーマンス監視ダッシュボード
- [ ] 設定プリセット機能

#### 中期（v1.3-1.5）
- [ ] 動画ファイル対応
- [ ] リアルタイム処理モード
- [ ] API化・外部連携
- [ ] クラウド処理オプション

#### 長期（v2.0+）
- [ ] 機械学習モデルの自動更新
- [ ] 多言語対応
- [ ] 企業向け管理機能
- [ ] モバイルアプリ版

### アーキテクチャ改善

#### 技術的負債解決
```python
# コード品質改善
- 型ヒント完全対応
- テストカバレッジ90%以上
- ドキュメント自動生成
- CI/CD パイプライン構築

# パフォーマンス最適化
- 非同期処理導入
- GPU並列処理対応
- メモリプール実装
- キャッシュシステム最適化
```

---

## 📚 参考資料・API仕様

### 主要クラス・関数リファレンス

#### DetectorクラS
```python
class MultiModelDetector:
    def __init__(self, config: ProcessingConfig, device: str = "auto"):
        """
        マルチモデル検出器の初期化
        
        Args:
            config: 処理設定
            device: 使用デバイス ("auto", "cpu", "cuda")
        """
        
    def detect(self, image: np.ndarray) -> List[BBoxWithClass]:
        """
        画像から対象物を検出
        
        Args:
            image: 入力画像 (BGR)
            
        Returns:
            検出結果のリスト
        """
```

#### Segmenterクラス  
```python
class GenitalSegmenter:
    def segment(self, image: np.ndarray, bboxes: List[BBox]) -> List[np.ndarray]:
        """
        バウンディングボックスからマスクを生成
        
        Args:
            image: 入力画像
            bboxes: バウンディングボックスリスト
            
        Returns:
            マスク画像のリスト
        """
```

### 設定ファイル仕様

#### ProcessingConfig
```python
@dataclass
class ProcessingConfig:
    # 検出設定
    confidence_threshold: float = 0.25
    nms_threshold: float = 0.45
    
    # セグメンテーション設定
    sam_use_vit_b: bool = True
    
    # モザイク設定
    mosaic_strength: float = 1.0
    edge_feathering: int = 5
    
    # カスタムモデル設定
    use_custom_models: bool = False
    custom_models: Dict[str, Dict] = field(default_factory=dict)
```

---

## 📞 開発者サポート

### 技術的質問・バグレポート

#### 情報収集テンプレート
```
環境情報:
- OS: Windows 10/11 (build番号)
- Python: 3.11.x
- CUDA: 12.8 (GPU使用時)
- アプリバージョン: v1.0.x

エラー詳細:
- エラーメッセージ: [全文]
- 発生タイミング: [起動時/処理中/終了時]
- 再現手順: [詳細な手順]
- ログファイル: [該当部分の抜粋]

使用画像情報:
- 形式: [JPEG/PNG/etc]
- サイズ: [1920x1080 etc]
- 枚数: [処理対象数]
```

### コントリビューション

#### プルリクエストガイドライン
```python
# コードスタイル
- PEP 8準拠
- 型ヒント必須
- ドキュメント文字列追加

# テスト要件
- 新機能には単体テスト必須
- 既存テストの通過確認
- パフォーマンステスト結果

# ドキュメント更新
- API変更時はドキュメント更新
- 使用例の追加
- 技術仕様の更新
```

---

**📝 このガイドは自動モザエセ v1.0の技術詳細に対応しています。**  
**🔄 最終更新: 2025年8月**  
**🔧 技術サポート: 統合認証システム、カスタムモデル対応、遅延ローダー、暗号化設定管理**  
**💬 技術的な質問や改善提案は、開発者コミュニティまでお気軽にお問い合わせください。** 