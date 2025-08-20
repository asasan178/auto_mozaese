# Discord認証設定ガイド

このガイドでは、自動モザエセでDiscord認証を正しく設定する方法を説明します。

## 🚨 404エラーの解決方法

配布版でDiscord認証時に404エラーが発生する場合、以下の手順で解決できます。

### 📋 Discord Developer Portalでの設定

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. あなたのアプリケーションを選択
3. **OAuth2** → **General** タブを開く
4. **Redirects** セクションで、以下のURLを**すべて**追加してください：

```
http://localhost:8000/callback
http://localhost:8080/callback
http://localhost:3000/callback
http://localhost:3001/callback
http://localhost:5000/callback
http://localhost:5001/callback
http://localhost:8001/callback
http://localhost:8081/callback
```

### 🔧 なぜ複数のURLが必要？

自動モザエセは動的ポート検出機能を使用しています：

- **ポート8000が使用中** → 自動的に8080を試す
- **8080も使用中** → 3000を試す
- **利用可能なポートを見つける** → そのポートでコールバックサーバーを起動

この仕組みにより、他のアプリケーションとのポート衝突を避けて認証を実行できます。

### 🎯 実装された改善点

#### 1. 動的ポート検出
```
- 推奨ポート（8000, 8080, 3000, 3001, 5000, 5001, 8001, 8081）を優先
- ポートが使用中の場合、自動的に次のポートを試行
- 最大10個のポートで検索
```

#### 2. 動的リダイレクトURI
```
- 実際に使用されたポートに基づいてリダイレクトURIを構築
- Discord APIリクエスト時に正しいURIを使用
- ログでどのポートが使用されたかを確認可能
```

#### 3. エラーハンドリング強化
```
- ポート取得失敗時の適切なエラーメッセージ
- デバッグ情報の詳細化
- フォールバック機能
```

## 🔍 トラブルシューティング

### ケース1: すべてのポートが使用中
```
エラー: "No available port found in range 8000-8009"
解決策: 
1. 他のアプリケーション（Webサーバー等）を一時停止
2. PCを再起動
3. ファイアウォール設定を確認
```

### ケース2: Discord Developer Portalの設定漏れ
```
エラー: "Discord token request failed: 400"
解決策:
1. 上記のリダイレクトURLがすべて登録されているか確認
2. Client IDとClient Secretが正しいか確認
```

### ケース3: ネットワーク接続問題
```
エラー: "Failed to start Discord callback server"
解決策:
1. インターネット接続を確認
2. VPNを一時的に無効化
3. ファイアウォールでlocalhostアクセスを許可
```

## 📝 ログでの確認方法

認証時のログで以下の情報を確認できます：

```
[INFO] Found available port (preferred): 8080
[INFO] Using dynamic redirect URI: http://localhost:8080/callback
[INFO] Opening Discord auth URL: https://discord.com/api/oauth2/authorize?...
[DEBUG] Token request using redirect_uri: http://localhost:8080/callback
```

## ✅ 正常動作の確認

1. Discord認証ダイアログでボタンをクリック
2. ブラウザが開き、Discordの認証ページが表示される
3. 認証後、成功ページが表示される
4. アプリケーション側で認証が完了する

## 📞 サポート

問題が解決しない場合は、以下の情報と共にお問い合わせください：

- 使用しているOS（Windows、Mac、Linux）
- エラーメッセージの全文
- 認証時のログ（個人情報は削除してください）
- Discord Developer Portalの設定スクリーンショット

---

**重要**: このガイドは配布版での404エラー解決を目的としています。開発版では異なる設定が必要な場合があります。
