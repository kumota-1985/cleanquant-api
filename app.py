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
import base64
import hashlib
import hmac
import time
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse, HTMLResponse

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA = "C:/omni_data" if os.path.isdir("C:/omni_data") else os.path.join(_HERE, "data")
DATA_DIR = os.environ.get("OMNI_DATA_DIR", _DEFAULT_DATA)     # ローカルはC:/omni_data、デプロイは同梱data
DEMO_LIMIT = 500
PRO_KEYS = set(k.strip() for k in os.environ.get("CLEANQUANT_KEYS", "").split(",") if k.strip())
RAPIDAPI_SECRET = os.environ.get("RAPIDAPI_PROXY_SECRET")     # RapidAPI出品時のプロキシ秘密(設定でRapidAPI経由のみ許可)
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")   # 直販の鍵自動発行/検証用(sk_live_...)
KEY_SIGNING_SECRET = os.environ.get("KEY_SIGNING_SECRET", "") # 直販APIキーのHMAC署名用ランダム秘密
DIRECT_AUTO = bool(STRIPE_SECRET_KEY and KEY_SIGNING_SECRET)  # 両方あれば鍵の自動発行/検証ON

_sub_cache = {}     # sub_id -> (is_active, expiry_ts) : Stripe照会の10分キャッシュ


# --------------------------------------------------------------------------- #
#  直販APIキー: Stripe購読ID を HMAC 署名(DB不要・メール不要・解約で自動失効)   #
# --------------------------------------------------------------------------- #
def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_key(sub_id: str) -> str:
    """Stripe サブスクID を署名した直販APIキー cq_<payload>.<sig> を発行する。"""
    payload = _b64(sub_id.encode())
    sig = hmac.new(KEY_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"cq_{payload}.{sig}"


def _key_sub_id(key: str):
    """署名が正しければ sub_id を返す(偽造は弾く)。"""
    if not key or not key.startswith("cq_") or "." not in key:
        return None
    payload, _, sig = key[3:].partition(".")
    expect = hmac.new(KEY_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        return _unb64(payload).decode()
    except Exception:
        return None


def _sub_active(sub_id: str) -> bool:
    """Stripe で購読が active/trialing か(10分キャッシュ)。解約されると自動でFalse。"""
    now = time.time()
    c = _sub_cache.get(sub_id)
    if c and c[1] > now:
        return c[0]
    active = False
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        sub = stripe.Subscription.retrieve(sub_id)
        active = sub.get("status") in ("active", "trialing")
    except Exception:
        active = False
    _sub_cache[sub_id] = (active, now + 600)
    return active


def verify_direct_key(key: str) -> bool:
    if not DIRECT_AUTO:
        return False
    sub_id = _key_sub_id(key)
    return bool(sub_id and _sub_active(sub_id))


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
    """True = pro(full) / False = demo(capped)。2チャネル同時対応:
    ① RapidAPI 経由 : RAPIDAPI_PROXY_SECRET 一致 → pro(課金/制限はRapidAPI側)
    ② 直販(手動)  : CLEANQUANT_KEYS に手動登録した鍵 → pro
    ② 直販(自動)  : Stripe決済で自動発行した cq_署名キー(購読が有効な間)→ pro
    ③ お試し       : X-API-Key=DEMO → demo(行数上限) / それ以外 → 拒否"""
    if RAPIDAPI_SECRET and rapid_secret == RAPIDAPI_SECRET:
        return True
    if x_api_key and x_api_key in PRO_KEYS:
        return True
    if isinstance(x_api_key, str) and x_api_key.startswith("cq_") and verify_direct_key(x_api_key):
        return True
    if x_api_key == "DEMO":
        return False
    raise HTTPException(status_code=401,
                        detail="Missing/invalid API key. Use 'DEMO' to try, or subscribe for a key.")


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


RATES_PUB_LAG_DAYS = 45    # FRED月次金利のおおよその公表ラグ(真のヴィンテージはALFRED連携で対応予定)


def _as_of_filter(df: pd.DataFrame, avail_col: str, as_of: Optional[str], lag_days: int = 0):
    """Point-in-Time: as_of 時点で『公開済み』だった行だけ残す(ルックアヘッド・バイアス排除)。"""
    if not as_of:
        return df
    cutoff = pd.to_datetime(as_of, errors="coerce")
    if pd.isna(cutoff):
        raise HTTPException(status_code=422, detail="as_of must be a date (YYYY-MM-DD)")
    a = pd.to_datetime(df[avail_col], errors="coerce")
    if getattr(a.dt, "tz", None) is not None:
        a = a.dt.tz_localize(None)
    if lag_days:
        a = a + pd.Timedelta(days=lag_days)
    return df[a <= cutoff]


def _check_format(fmt: str):
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=422, detail="format must be 'json' or 'csv'")


def _respond(df: pd.DataFrame, fmt: str, pro: bool, time_col: str, extra: Optional[dict] = None):
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
    body = {"count": len(df), "tier": "pro" if pro else "demo",
            "data": df.to_dict(orient="records")}
    if extra:
        body.update(extra)
    return JSONResponse(body)


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


@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
def llms_txt():
    """AIエージェント/検索AI 向けの自己紹介(自動発見・推薦の導線)。"""
    return """# CleanQuant Data API
> Backtest-ready alternative data for quants. Point-in-time (?as_of=), no look-ahead bias.

Base URL: https://cleanquant-api.onrender.com
Docs: https://cleanquant-api.onrender.com/docs
OpenAPI: https://cleanquant-api.onrender.com/openapi.json

## Endpoints
- GET /v1/cot?market=EURUSD - CFTC COT speculator positioning, weekly (public domain)
- GET /v1/rates?ccy=EUR - 3M interbank rates + USD differential (OECD via FRED; cite OECD)
- All accept ?as_of=YYYY-MM-DD (point-in-time) and ?format=json|csv
- Auth: header X-API-Key (use DEMO to try)

Datasets are limited to redistribution-clean public sources (CFTC public-domain, OECD-via-FRED with citation).
"""


@app.get("/v1/activate", response_class=HTMLResponse, include_in_schema=False)
def activate(session_id: str = ""):
    """Stripe決済の完了ページ。session_id を検証し、購読が有効ならAPIキーを発行・表示する。"""
    if not DIRECT_AUTO:
        return HTMLResponse("<p>Key auto-issue is not configured on this server.</p>", status_code=503)
    if not session_id:
        return HTMLResponse("<p>Missing session_id.</p>", status_code=400)
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        sess = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        return HTMLResponse("<p>Could not verify your checkout session.</p>", status_code=400)
    paid = sess.get("payment_status") == "paid" or sess.get("status") == "complete"
    sub_id = sess.get("subscription")
    if not (paid and sub_id):
        return HTMLResponse("<p>Payment not completed yet. If you just paid, refresh in a moment.</p>",
                            status_code=402)
    key = mint_key(sub_id)
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;max-width:680px;margin:48px auto;color:#1a1f2b'>"
        "<h2>&#9989; Subscription active &mdash; your API key</h2>"
        "<p>Send it in the <code>X-API-Key</code> header on every request. Keep it safe.</p>"
        f"<pre style='background:#f1f3f7;padding:14px;border-radius:8px;user-select:all'>{key}</pre>"
        "<p>Example:</p>"
        f"<pre style='background:#f1f3f7;padding:14px;border-radius:8px'>curl -H \"X-API-Key: {key}\" \\\n"
        "  \"https://cleanquant-api.onrender.com/v1/cot?market=EURUSD&amp;as_of=2024-06-01\"</pre>"
        "<p style='color:#5b6472'>Access stays active while your subscription is active.</p>"
        "</body></html>")


OECD_ATTRIBUTION = ("Source: OECD Main Economic Indicators, 3-month interbank rates, "
                    "retrieved via FRED (Federal Reserve Bank of St. Louis). "
                    "© OECD — citation required.")


@app.get("/v1/catalog")
def catalog():
    """配信中のデータセット一覧(営業・買い手向けの目録)。
    再配布クリーンな公開ソースのみ(CFTC=パブリックドメイン / OECD-via-FRED=出典明記)。"""
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
            "cot": {"desc": "CFTC COT speculator positioning (weekly)", "source": "CFTC (public domain)",
                    "markets": cot_markets, "endpoint": "/v1/cot"},
            "rates": {"desc": "3M interbank rates & USD diff", "source": "OECD via FRED",
                      "attribution": OECD_ATTRIBUTION, "currencies": rate_ccys, "endpoint": "/v1/rates"},
        },
        "auth": {"demo_key": "DEMO", "demo_row_cap": DEMO_LIMIT,
                 "pro": "set CLEANQUANT_KEYS env to enable full-access keys"},
    }


# NOTE: /v1/funding (Binance perp funding) and /v1/dvol (Deribit DVOL) were removed:
# both exchanges' Terms forbid commercial redistribution of their market data without a
# written license. Only redistribution-clean sources are served (CFTC public-domain, OECD-via-FRED).


@app.get("/v1/cot")
def cot(market: Optional[str] = None,
        start: Optional[str] = None, end: Optional[str] = None,
        as_of: Optional[str] = None,
        format: str = "json",
        x_api_key: Optional[str] = Header(None),
        x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """CFTC COT 投機筋ネットポジショニング(net_frac = 投機筋ネット比率)。
    as_of=YYYY-MM-DD で『その日までに公表(avail)済み』の週次レポートのみ = 真のPoint-in-Time。"""
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("cot", "cot_fx.parquet")
    if market:
        df = df[df["pair"].astype(str).str.upper() == market.upper()]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"unknown market: {market}")
    df = _slice_time(df, "date", start, end)
    df = _as_of_filter(df, "avail", as_of)
    return _respond(df, format, pro, "date")


@app.get("/v1/rates")
def rates(ccy: Optional[str] = None,
          start: Optional[str] = None, end: Optional[str] = None,
          as_of: Optional[str] = None,
          format: str = "json",
          x_api_key: Optional[str] = Header(None),
          x_rapidapi_proxy_secret: Optional[str] = Header(None)):
    """FRED/OECD 3ヶ月金利と対USD金利差(diff)。as_of=YYYY-MM-DD で公表ラグ込みのPIT近似
    (真のヴィンテージ=ALFRED連携は今後)。OECD出典の明記が必要(レスポンスに attribution を同梱)。"""
    _check_format(format)
    pro = auth(x_api_key, x_rapidapi_proxy_secret)
    df = _read("macro", "rates_fred.parquet")
    if ccy:
        df = df[df["ccy"].astype(str).str.upper() == ccy.upper()]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"unknown ccy: {ccy}")
    df = _slice_time(df, "date", start, end)
    df = _as_of_filter(df, "date", as_of, lag_days=RATES_PUB_LAG_DAYS)
    return _respond(df, format, pro, "date", extra={"attribution": OECD_ATTRIBUTION})
