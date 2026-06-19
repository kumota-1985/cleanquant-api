# デプロイ & RapidAPI 出品 手順

目的:このフォルダを公開デプロイ → RapidAPI に出品 → **検索経由で勝手に買い手が来る**状態にする。
英語の出品文は [RAPIDAPI_LISTING.md](RAPIDAPI_LISTING.md) に用意済み(貼るだけ)。

---

## ステップ1:GitHub に上げる(Render が読むため)

このフォルダ(`flip_dataapi`)を1つのGitリポジトリにして push する。`data/`(同梱データ1.9MB)も一緒に上げる(デプロイに必要・公開ソースのみなので問題なし)。

```powershell
cd C:\TOREADING－AI\flip_dataapi
git init
git add .
git commit -m "CleanQuant data API"
# GitHubで空リポジトリを作成 → そのURLを使う:
git remote add origin https://github.com/<あなた>/cleanquant-api.git
git branch -M main
git push -u origin main
```
> 鍵やパスワードはコード内に無い(全て環境変数)。秘密情報は上がらない。

## ステップ2:Render で公開(無料)

1. [render.com](https://render.com) に登録(GitHubでログインが楽)
2. **New → Blueprint** → さっきのリポジトリを選択(`render.yaml` を自動で読む)
   - もしくは **New → Web Service** で手動設定:
     - Build: `pip install -r requirements.txt`
     - Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
     - Env: `OMNI_DATA_DIR = data`
3. デプロイ完了 → `https://cleanquant-api.onrender.com` のような**公開URL**が出る
4. 動作確認:ブラウザで `https://<あなたのURL>/docs` を開く / `…/v1/catalog` が返るか見る
   - 無料プランは無アクセスでスリープ→初回が遅い。これは仕様。

## ステップ3:RapidAPI に出品

1. [rapidapi.com](https://rapidapi.com) → **My APIs → Add New API**(REST)
2. **Base URL** に Render の公開URLを設定
3. **Endpoints** を追加(`/v1/catalog` `/v1/funding` `/v1/cot` `/v1/rates` `/v1/dvol`)— 説明は [RAPIDAPI_LISTING.md](RAPIDAPI_LISTING.md) の英語を貼る
4. **セキュリティ(重要)**:RapidAPI が発行する **Proxy Secret** をコピー →
   Render の Environment に `RAPIDAPI_PROXY_SECRET = <そのProxy Secret>` を追加して再デプロイ。
   → これで「RapidAPI経由のリクエストだけ通る」=URL直叩きの無銭飲食を防げる。
5. **Plans(料金)** を設定(BASIC無料 / PRO $9.99 …。[RAPIDAPI_LISTING.md](RAPIDAPI_LISTING.md) の表)
6. **Public** で公開 → RapidAPI の検索に載る。**鍵発行・課金・上限管理は全部RapidAPIが代行。**

---

## 正直な注意

- **「宣伝ゼロ」ではなく「最小限」**。出品文・タグ・SEOを丁寧に書くほど検索で見つかる。出して様子を見る=**低宣伝の需要テスト**。
- 売れるのは**公開ソース由来データのみ**(funding/COT/FRED/DVOL)。XMブローカーのデータは出さない。
- 本番運用するなら、データを**定期再取得**して新鮮に保つ(後で cron 化を組める)。
- 購読者が安定したら、**Acquire/Flippa でまるごと売却**(=まとまった一括金)も可能。

## 困ったら

各ステップで詰まったら、画面を見せてください。Render設定・RapidAPI登録・git push、どこでも一緒に進めます。
