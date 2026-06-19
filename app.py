#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CleanQuant Data API  --  flip_dataapi/app.py   (build-to-flip MVP #1)
================================================================================
個人クオンツ/研究者向けの "backtest-ready alternative data" を1コールで返すAPI。
売り物にできる = 一次の公開ソース由来のみを配信する:
  - funding : 無期限スワップの資金調達率(Binance 公開API由来)
  - cot     : CFTC COT 投機筋ポジショニング(米政府・パブリックドメイン)
  - rates   : FRED/OECD 主要通貨3ヶ月金利と対USD金利差
  - dvol    : Deribit DVOL(クリプトIV指数)
※ XM/ブローカー専有のbars(FX/株/指数)は再配布不可のため *配信しない*。

付加価値 = 整形・ISO時刻・point-in-time・1コール・freemium。
MVPは既存の parquet (C:/omni_data) をそのまま配信(本番は定期再取得に差し替え)。

  pip install -r requirements.txt
  uvicorn app:app --reload --port 8000
  → http://127.0.0.1:8000/docs  (自動ドキュメント=営業資料にもなる)

無料デモ: ヘッダ X-API-Key: DEMO  (各レスポンス最大 limit=500 行)
有料相当: 環境変数 CLEANQUANT_KEYS="key1,key2" を設定したキーは全件・全範囲
"""
import io
import os
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse, HTMLResponse

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA = "C:/omni_data" if os.path.isdir("C:/omni_data") else os.path.join(_HERE, "data")
DATA_DIR = os.environ.get("OMNI_DATA_DIR", _DEFAULT_DATA)     # ローカルはC:/omni_data、デプロイは同梱data
DEMO_LIMIT = 500
PRO_KEYS = set(k.strip() for k in os.environ.get("CLEANQUANT_KEYS", "").split(",") if k.strip())
RAPIDAPI_SECRET = os.environ.get("RAPIDAPI_PROXY_SECRET")     # RapidAPI出品時のプロキシ秘密(設定でRapidAPI経由のみ許可)

app = FastAPI(
    title="CleanQuant Data API",
    version="0.1.0",
    description="Backtest-ready alternative data for indie quants. "
                "Crypto funding rates, CFTC COT positioning, FRED macro rates, Deribit DVOL — "
                "cleaned, ISO-timestamped, point-in-time. One API call.",
)


# --------------------------------------------------------------------------- #
#  auth (freemium): DEMO = capped rows / PRO = full                            #
# --------------------------------------------------------------------------- #
def auth(x_api_key: Optional[str], rapid_secret: Optional[str] = None) -> bool:
    """True = pro(full), False = demo(capped)。
    RapidAPI出品時: RAPIDAPI_PROXY_SECRET を設定すると RapidAPI プロキシ経由のみ許可
    (課金/レート制限は RapidAPI 側が担うので、一致すれば全件 pro)。"""
    if RAPIDAPI_SECRET:
        if rapid_secret == RAPIDAPI_SECRET:
            return True
        raise HTTPException(status_code=403, detail="Requests must go through the RapidAPI marketplace.")
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header. Use 'DEMO' to try.")
    if x_api_key in PRO_KEYS:
        return True
    if x_api_key == "DEMO":
        return False
    raise HTTPException(status_code=403, detail="Invalid API key.")


def _read(*parts) -> pd.DataFrame:
    p = os.path.join(DATA_DIR, *parts)
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail=f"dataset not found: {'/'.join(parts)}")
    return pd.read_parquet(p)


def _slice_time(df: pd.DataFrame, col: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    t = pd.to_datetime(df[col])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_localize(None)
    df = df.assign(**{col: t}).sort_values(col)
    if start:
        df = df[df[col] >= pd.to_datetime(start)]
    if end:
        df = df[df[col] <= pd.to_datetime(end)]
    return df


def _check_format(fmt: str):
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=422, detail="format must be 'json' or 'csv'")


def _respond(df: pd.DataFrame, fmt: str, pro: bool, time_col: str):
    df = df.copy()
    for col in df.columns:                      # 全日時列を ISO 文字列化(NaT→null)
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            mask = df[col].notna()
            df[col] = df[col].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            df.loc[~mask, col] = None
    if not pro and len(df) > DEMO_LIMIT:
        df = df.tail(DEMO_LIMIT)
    if fmt == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")
    return JSONResponse({"count": len(df), "tier": "pro" if pro else "demo",
                         "data": df.to_dict(orient="records")})


# --------------------------------------------------------------------------- #
#  endpoints                                                                   #
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return ('<h2>CleanQuant Data API</h2>'
            '<p>Backtest-ready alternative data for indie quants.</p>'
            '<p>→ <a href="/docs">/docs</a> for interactive API. '
            'Try header <code>X-API-Key: DEMO</code>.</p>'
            '<p>Datasets: <a href="/v1/catalog">/v1/catalog</a></p>')


@app.get("/v1/catalog")
def catalog():
    """配信中のデータセット一覧(営業・買い手向けの目録)。"""
    crypto_dir = os.path.join(DATA_DIR, "crypto")
    funding_syms = sorted(d for d in os.listdir(crypto_dir)) if os.path.isdir(crypto_dir) else []
    cot_markets = rate_ccys = []
    try:
        cot_markets = sorted(_read("cot", "cot_fx.parquet")["pair"].dropna().unique().tolist())
    except Exception:
        pass
    try:
        rate_ccys = sorted(_read("macro", "rates_fred.parquet")["ccy"].dropna().unique().tolist())
    except Exception:
        pass
    return {
        "datasets": {
            "funding": {"desc": "Perp funding rates (8h)", "source": "Binance public API",
                        "symbols": funding_syms, "endpoint": "/v1/funding"},
            "cot": {"desc": "CFTC COT speculator positioning (weekly)", "source": "CFTC (public domain)",
                    "markets": cot_markets, "endpoint": "/v1/cot"},
            "rates": {"desc": "3M interbank rates & USD diff", "source": "FRED / OECD",
                      "currencies": rate_ccys, "endpoint": "/v1/rates"},
            "dvol": {"desc": "Deribit DVOL crypto implied-vol index", "source": "Deribit public API",
                     "assets": ["btc", "eth"], "endpoint": "/v1/dvol"},
        },
        "auth": {"demo_key": "DEMO", "demo_row_cap": DEMO_LIMIT,
                 "pro": "set CLEANQUANT_KEYS env to enable full-access keys"},
    }


@app.get("/v1/funding")
def funding(symbol: str = Query(...),
            start: Optional[str] = None, end: Optional[str] = None,
            format: str = "json",
            x_api_key: Optional[str] = Header(None),
            x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """無期限スワップの資金調達率(8時間ごと)。"""
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("crypto", symbol.upper(), "funding.parquet")[["time", "fundingRate", "symbol"]]
    df = _slice_time(df, "time", start, end)
    return _respond(df, format, pro, "time")


@app.get("/v1/cot")
def cot(market: Optional[str] = None,
        start: Optional[str] = None, end: Optional[str] = None,
        format: str = "json",
        x_api_key: Optional[str] = Header(None),
        x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """CFTC COT 投機筋ネットポジショニング(net_frac = 投機筋ネット比率)。"""
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("cot", "cot_fx.parquet")
    if market:
        df = df[df["pair"].astype(str).str.upper() == market.upper()]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"unknown market: {market}")
    df = _slice_time(df, "date", start, end)
    return _respond(df, format, pro, "date")


@app.get("/v1/rates")
def rates(ccy: Optional[str] = None,
          start: Optional[str] = None, end: Optional[str] = None,
          format: str = "json",
          x_api_key: Optional[str] = Header(None),
          x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """FRED/OECD 3ヶ月金利と対USD金利差(diff)。"""
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("macro", "rates_fred.parquet")
    if ccy:
        df = df[df["ccy"].astype(str).str.upper() == ccy.upper()]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"unknown ccy: {ccy}")
    df = _slice_time(df, "date", start, end)
    return _respond(df, format, pro, "date")


@app.get("/v1/dvol")
def dvol(asset: str = "btc",
         start: Optional[str] = None, end: Optional[str] = None,
         format: str = "json",
         x_api_key: Optional[str] = Header(None),
         x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """Deribit DVOL(クリプトのインプライド・ボラ指数)。"""
    if asset.lower() not in ("btc", "eth"):
        raise HTTPException(status_code=422, detail="asset must be 'btc' or 'eth'")
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("macro", f"dvol_{asset.lower()}.parquet")[["time", "dvol"]]
    df = _slice_time(df, "time", start, end)
    return _respond(df, format, pro, "time")
