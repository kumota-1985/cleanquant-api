# RapidAPI 出品用テキスト(英語=そのまま貼る / 日本語=やり方)

RapidAPI Hub の各入力欄に、下の **English ブロックをコピペ**してください。英語は書けなくてOK、用意済みです。

---

## API Name(API名)
```
CleanQuant — Backtest-Ready Alternative Data
```

## Short tagline(短い説明)
```
Crypto funding rates, CFTC COT positioning, FRED macro rates, and Deribit DVOL — cleaned, ISO-timestamped, point-in-time. One call, JSON or CSV.
```

## Category / Tags(カテゴリ・タグ)
```
Category: Finance
Tags: finance, crypto, trading, quant, dataset, funding-rate, macro, volatility, backtest
```

## Long Description(詳細説明 / Overview 欄)
```
CleanQuant gives indie quants and researchers backtest-ready alternative data through a single, simple API — no scraping, no CSV wrangling, no look-ahead bugs.

Datasets:
- Funding rates: 8-hour perpetual-swap funding history for 15+ symbols (source: Binance public API).
- COT positioning: CFTC Commitments of Traders speculator net positioning, weekly (source: CFTC, public domain).
- Macro rates: 3-month interbank rates and USD rate differentials for major currencies (source: FRED / OECD).
- DVOL: Deribit crypto implied-volatility index for BTC and ETH (source: Deribit public API).

Every series is cleaned, ISO-8601 timestamped, and point-in-time aligned so you can drop it straight into a backtest. Responses in JSON or CSV. Start free, scale when you need to.

Independent project; not affiliated with the data sources above.
```

---

## Endpoints(エンドポイント定義)

各エンドポイントを RapidAPI の "Endpoints" で追加し、Description に英語を貼る。

### GET `/v1/catalog`
```
List all available datasets and their symbols/markets/currencies.
```

### GET `/v1/funding`
```
Perpetual-swap funding rate history (8h). 
Params: symbol (required, e.g. BTCUSDT) | start (optional, YYYY-MM-DD) | end (optional) | format (json|csv)
Example: /v1/funding?symbol=BTCUSDT&format=csv
```

### GET `/v1/cot`
```
CFTC COT speculator net positioning (weekly). 
Params: market (optional, e.g. EURUSD) | start | end | format (json|csv)
Example: /v1/cot?market=EURUSD
```

### GET `/v1/rates`
```
FRED/OECD 3-month interbank rates and USD differential. 
Params: ccy (optional, e.g. EUR) | start | end | format (json|csv)
Example: /v1/rates?ccy=EUR
```

### GET `/v1/dvol`
```
Deribit DVOL crypto implied-volatility index. 
Params: asset (btc|eth) | start | end | format (json|csv)
Example: /v1/dvol?asset=btc
```

---

## Pricing tiers(料金プラン例 — RapidAPIの Plans 欄で設定)

| Plan | 月額 | 上限/月 | 超過 |
|---|---|---|---|
| **BASIC** | $0 | 500 requests | ハード上限(無料お試し) |
| **PRO** | $9.99 | 50,000 requests | $0.0005 / req |
| **ULTRA** | $29.99 | 500,000 requests | $0.0002 / req |
| **MEGA** | $99.00 | 5,000,000 requests | $0.0001 / req |

> 無料枠で釣り、使う人だけ課金。RapidAPIが**鍵発行・課金・上限管理を全部代行**するので、あなたは何もしない。

---

## SEO keywords(検索で見つけてもらう / Hub の SEO 欄)
```
crypto funding rate api, cot report api, cftc positioning data, fred interest rate api, deribit dvol api, alternative data api, quant data, backtest data, point in time financial data
```
