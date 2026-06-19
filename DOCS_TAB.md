# Docs タブに貼る内容(英語・Markdown)

RapidAPIの **Docs**(About)タブに、下の `---` 内の英語Markdownをそのまま貼ってください。

---

# CleanQuant API — Documentation

Backtest-ready alternative data for indie quants and researchers. Four datasets, one consistent API. Responses are **cleaned, ISO-8601 timestamped, and point-in-time** (no look-ahead).

## Authentication

You don't manage any keys yourself. **Subscribe to a plan** (BASIC is free), then use the auto-generated code snippets on the **Endpoints** tab — RapidAPI injects your `X-RapidAPI-Key` and `X-RapidAPI-Host` headers automatically. Just call the endpoint and you get data back.

## Response format

Every data endpoint accepts `format=json` (default) or `format=csv`.

JSON shape:
```json
{ "count": 123, "tier": "pro", "data": [ { ... }, { ... } ] }
```
- `count` — number of rows returned
- `tier` — your access tier
- `data` — the records (newest last)

All endpoints accept optional `start` and `end` (`YYYY-MM-DD`) to slice by date.

---

## GET /v1/catalog
Lists every dataset and its available symbols, markets, and currencies. No parameters.

## GET /v1/funding
8-hour perpetual-swap **funding rates** (source: Binance public API).

| Param | Required | Example | Notes |
|---|---|---|---|
| `symbol` | yes | `BTCUSDT` | 15+ symbols (see /v1/catalog) |
| `start` / `end` | no | `2024-01-01` | date range |
| `format` | no | `json` | `json` or `csv` |

**Example:** `GET /v1/funding?symbol=BTCUSDT&format=csv`
```json
{ "count": 2, "tier": "pro",
  "data": [ { "time": "2026-06-03T16:00:00Z", "fundingRate": 0.0001, "symbol": "BTCUSDT" } ] }
```

## GET /v1/cot
Weekly **CFTC COT** speculator net positioning for major FX (source: CFTC, public domain).

| Param | Required | Example |
|---|---|---|
| `market` | no | `EURUSD` |
| `start` / `end` | no | `2024-01-01` |
| `format` | no | `json` / `csv` |

**Example:** `GET /v1/cot?market=EURUSD`
```json
{ "count": 1, "tier": "pro",
  "data": [ { "date": "2026-06-10T00:00:00Z", "market": "EURO FX", "pair": "EURUSD",
              "oi": 712345, "ncl": 210345, "ncs": 150220, "net_frac": 0.18,
              "avail": "2026-06-16T00:00:00Z" } ] }
```
`net_frac` = speculator net position as a fraction. `avail` = the date this report became publicly available (use it to avoid look-ahead).

## GET /v1/rates
3-month interbank **rates** and USD differential for 7 major currencies (source: FRED / OECD).

| Param | Required | Example |
|---|---|---|
| `ccy` | no | `EUR` |
| `start` / `end` | no | `2024-01-01` |
| `format` | no | `json` / `csv` |

**Example:** `GET /v1/rates?ccy=EUR`
```json
{ "count": 1, "tier": "pro",
  "data": [ { "date": "2026-06-01T00:00:00Z", "ccy": "EUR", "rate": 3.40, "us_rate": 5.10, "diff": -1.70 } ] }
```
`diff` = ccy rate − USD rate (the carry differential).

## GET /v1/dvol
**Deribit DVOL** crypto implied-volatility index.

| Param | Required | Example |
|---|---|---|
| `asset` | no | `btc` or `eth` |
| `start` / `end` | no | `2024-01-01` |
| `format` | no | `json` / `csv` |

**Example:** `GET /v1/dvol?asset=btc`
```json
{ "count": 1, "tier": "pro", "data": [ { "time": "2026-06-12T00:00:00Z", "dvol": 48.3 } ] }
```

---

## Data sources & disclaimer
Data is sourced from public providers: Binance, CFTC, FRED/OECD, and Deribit. This is an independent project and is not affiliated with, or endorsed by, these providers. Provided as-is for research and backtesting.
