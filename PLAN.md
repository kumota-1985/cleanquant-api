# CleanQuant Data API — build-to-flip 計画

**目的:** 「作って売る」最初の1本。あなたの既存pullerを、堂々と再配布できる公開ソースのデータだけに絞って、
clean な有料APIに転生させる。継続課金(MRR)を少し付けて、Acquire/Flippa で **月利益の3〜5倍の一括金**で売却する。

---

## 何ができたか(このリポジトリ)

- `app.py` — FastAPI。`funding / cot / rates / dvol` を JSON/CSV で配信。freemium(DEMO鍵=最大500行、PRO鍵=全件)。`/docs` 自動ドキュメント付き。
- `web/index.html` — 需要テスト用ランディングページ(先行登録フォーム)。
- `requirements.txt` — Python 3.8 互換ピン留め。

ローカル起動:
```
pip install -r requirements.txt
uvicorn app:app --port 8000      # flip_dataapi/ で実行
# → http://127.0.0.1:8000/docs
# 試す: curl -H "X-API-Key: DEMO" "http://127.0.0.1:8000/v1/funding?symbol=BTCUSDT&format=csv"
```

---

## 売り物にできるデータの線引き(重要・正直に)

| データ | ソース | 再配布 | 配信する? |
|---|---|---|---|
| funding | Binance 公開API | 公開市場データ(慣行上ベンダー多数) | ✅ |
| cot | CFTC | **米政府・パブリックドメイン** | ✅ |
| rates | FRED/OECD | 公開(出典明記) | ✅ |
| dvol | Deribit 公開API | 公開 | ✅ |
| **bars(FX/株/指数)** | **XMブローカー専有** | **❌ ToS違反** | **配信しない** |

→ 付加価値は「データそのもの」でなく **整形・整列・point-in-time・1コール・freemium** の利便性。これは正当な商品。
本番ローンチ前に各ソースの最新ToS(特にBinance/Deribitの商用再配布条項)を一度確認すること。

---

## 7日プラン(まず需要、次に出荷)

**Day 1–2:需要テスト(あなたしかできない)**
- [ ] 無料の Formspree か Tally でフォーム作成 → `web/index.html` の `action="https://formspree.io/f/REPLACE_ME"` を自分のURLに差し替え
- [ ] LP を無料ホスティングに公開(Cloudflare Pages / Netlify / GitHub Pages のどれか。静的1ファイルなので5分)
- [ ] 流入を作る:r/algotrading、quant系Discord/Slack、X、IndieHackers に「個人クオンツ向けの綺麗なfunding/COT/FRED API作ってる、欲しい人いる?」と1投稿ずつ

**Day 3–5:MVPを公開状態に**
- [ ] PRO鍵を環境変数 `CLEANQUANT_KEYS` で発行する運用を決める(MVPは手動発行で十分)
- [ ] `app.py` を無料/格安ホスティングにデプロイ(Render / Railway / Fly.io 無料枠)。データparquetも一緒に上げる
- [ ] Stripe Payment Link を1本作る($9/mo)。買ったら鍵を手動メール(自動化は後)

**Day 6–7:判定**
- [ ] 合格ライン:**メール30件 or 課金1件** → 本命。続行
- [ ] 未達 → このデータ需要は薄い。LPの反応(どのデータに反応したか)を見て pivot、または候補2/3へ

---

## 売却(flip)まで

1. 課金ユーザーが数件付き、MRRが安定(解約が少ない)
2. 定期再取得を cron 化(運営者依存を下げる=買い手が嫌う「あなたがいないと止まる」を消す)
3. 売上・原価・チャーンを3〜6ヶ月記録
4. Acquire / Flippa に出品。継続収入のあるニッチAPIは **年利益の3〜5倍** が目安

---

## あなたがやること vs 僕がやること

- **あなた(今日)**:Formspree/Tally作成 → LP差し替え&公開 → 3コミュニティに投稿。(=需要テストの開始。コードでなく人に当てる工程)
- **僕(言ってくれれば)**:デプロイ手順の具体化、Stripe連携で鍵を自動発行する小コード、定期再取得スクリプト、LP文言のA/B、出品ページのドラフト。
