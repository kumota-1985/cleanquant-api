# 出品コピー v2(Point-in-Time 前面・痛み訴求)— RapidAPIに貼り替え

リサーチの最重要指摘(ルックアヘッド・バイアス / point-in-time)を反映した版。
General タブの該当欄を、下の英語に**貼り替え**てください。

## Short Description(貼り替え)
```
Point-in-time alternative data for quants — add ?as_of=DATE and get only what was knowable then. Crypto funding, CFTC COT, FRED rates, Deribit DVOL. No look-ahead bias. JSON/CSV.
```

## Long Description(貼り替え / Markdown)
```markdown
## Your backtest is eating future data.

Scraped FRED series get silently revised. Raw exchange funding history mixes in information that didn't exist at trade time. The result: a backtest Sharpe that looks 1.5+ — and evaporates the moment you go live. Look-ahead bias has killed more "edges" than bad models ever have.

**CleanQuant returns only what the market actually knew on a given date.** Add `?as_of=2024-06-01` to any endpoint for a true point-in-time snapshot — no future leakage.

### Datasets
- **Crypto funding rates** — 8h perpetual-swap history, 15+ symbols (Binance).
- **CFTC COT positioning** — weekly speculator net, point-in-time by *publish date*: a report dated Tuesday isn't returned until it was actually released.
- **FRED macro rates** — 3-month interbank + USD differential, publication-lag aware.
- **Deribit DVOL** — BTC/ETH implied-volatility index.

### Why CleanQuant
- **`?as_of=` point-in-time** — the feature that separates a real backtest from a fairy tale.
- **One call, JSON or CSV** — drop straight into pandas.
- **Cleaned, ISO-8601, consistent schema** — no scraping, no parsing, no timezone headaches.
- **Free tier** — try every dataset before you pay.

`GET /v1/cot?market=EURUSD&as_of=2024-06-01`

_Independent project; not affiliated with the data sources above._
```

## Docs タブに追記(Point-in-Time セクション)
```markdown
## Point-in-Time (`as_of`)

Add `?as_of=YYYY-MM-DD` to any data endpoint to get **only what was knowable on that date** — the single most important defense against look-ahead bias.

- **funding / dvol**: returns observations with timestamp <= as_of.
- **cot**: returns only reports whose *publication date* (release, ~6 days after the as-of Tuesday) is <= as_of. A report that existed but wasn't public yet is correctly excluded.
- **rates**: applies a publication lag (true as-reported ALFRED vintages coming soon).

Example — what an EURUSD COT model could legitimately see on 2024-06-01:
`GET /v1/cot?market=EURUSD&as_of=2024-06-01`
```

## RapidAPI側でやること
1. **General**: Short / Long Description を上記に貼り替え(カードとOverviewが痛み訴求に)。
2. **Definitions → Endpoints**: 各エンドポイントに `as_of`(query, optional)パラメータを追加。
   - もしくは Studio で `openapi_rapidapi.json`(更新済・as_of入り)を**再インポート**するのが速い。
3. **Docs**: 上の「Point-in-Time」セクションを追記。
4. 価格はリサーチ推奨に寄せるなら: Indie $49 / Pro $149 等への見直しも検討(任意)。
