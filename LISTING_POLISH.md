# 出品を「売れやすく」する仕上げ(コピペ用)

## 1. ロゴ(General → Upload Logo)
ファイル: `flip_dataapi/cleanquant_logo.png`(500x500 PNG)を **Upload Logo** にアップ。

## 2. Long Description(General → Long Description に貼る / Markdown可)
```markdown
## CleanQuant — Backtest-Ready Alternative Data

Stop scraping and re-aligning data for every backtest. CleanQuant delivers four high-signal datasets through one simple API — already cleaned, ISO-8601 timestamped, and point-in-time aligned (no look-ahead).

### Datasets
- **Funding rates** — 8-hour perpetual-swap funding history for 15+ symbols (BTC, ETH, SOL, and more). Source: Binance public API.
- **COT positioning** — CFTC Commitments of Traders speculator net positioning, weekly, for major FX. Source: CFTC (public domain).
- **Macro rates** — 3-month interbank rates and USD rate differentials for 7 major currencies. Source: FRED / OECD.
- **DVOL** — Deribit crypto implied-volatility index for BTC and ETH.

### Why CleanQuant
- **One call, JSON or CSV** — drop straight into pandas or your backtester.
- **Point-in-time, no look-ahead** — built by a quant tired of subtle data leaks.
- **Clean, consistent schema** — no scraping, no parsing, no timezone headaches.
- **Free tier** — try every dataset before you pay.

### Quickstart
`GET /v1/funding?symbol=BTCUSDT&format=csv`

_Independent project; not affiliated with the data sources above._
```

## 3. Health Check URL(General → Health Check URL)
`/ping` の所を **`/v1/catalog`** に変更(存在する端点なので死活監視が通る=健全に見える)。

## 4. タグ / SEO(Hub Listing のタグ欄に追加)
```
crypto, finance, trading, quant, funding-rate, cot, cftc, fred, interest-rates, volatility, dvol, dataset, backtest, market-data, alternative-data
```

## 5. (任意)Docs/About タブ
「使い方」を一言:無料BASICで試す → PRO以上で本番。各endpointは `format=json|csv`、`start`/`end` で期間指定可。
