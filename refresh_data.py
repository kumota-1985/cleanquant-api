#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_data.py — 公開ソースから全データセットを再取得し ./data を更新(CI/cron用)。
すべて認証不要の公開API。GitHub Actions が週次で実行 → 変更を commit → Render が自動再デプロイ。

  python refresh_data.py            # 全部(funding rates cot dvol)
  python refresh_data.py dvol cot   # 一部だけ

funding/cot は既存データとマージ(履歴維持・増分追加)、rates/dvol は全期間を再取得。
"""
import io
import os
import sys
import time
import json
import zipfile
import urllib.request
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("OMNI_DATA_DIR", os.path.join(HERE, "data"))

FUNDING_SYMBOLS = ["ADAUSDT", "APTUSDT", "ARBUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT",
                   "DOGEUSDT", "DOTUSDT", "ETHUSDT", "INJUSDT", "LINKUSDT", "LTCUSDT",
                   "NEARUSDT", "SOLUSDT", "XRPUSDT"]
FULL_YEARS = float(os.environ.get("REFRESH_YEARS", "3"))


def _get_json(url, tries=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(1.5 * (a + 1))


def _get_bytes(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# --------------------------------------------------------------------------- #
#  funding (Binance USDⓈ-M perp) — 既存とマージ                                #
# --------------------------------------------------------------------------- #
def refresh_funding():
    BASE = "https://fapi.binance.com"
    now = _now_ms()
    ok = 0
    for sym in FUNDING_SYMBOLS:
        try:
            dd = os.path.join(DATA, "crypto", sym)
            fpath = os.path.join(dd, "funding.parquet")
            old = pd.read_parquet(fpath) if os.path.exists(fpath) else pd.DataFrame()
            if not old.empty:
                last = int(pd.to_datetime(old["time"]).max().timestamp() * 1000)
                start = last - 2 * 86400 * 1000           # 2日重ねて取りこぼし防止
            else:
                start = now - int(FULL_YEARS * 365.25 * 86400 * 1000)
            out, cur = [], start
            while cur < now:
                d = _get_json(BASE + "/fapi/v1/fundingRate?" + urllib.parse.urlencode(
                    dict(symbol=sym, startTime=cur, endTime=now, limit=1000)))
                if not d:
                    break
                out += d
                last_ms = d[-1]["fundingTime"]
                if last_ms <= cur:
                    break
                cur = last_ms + 1
                if len(d) < 1000:
                    break
                time.sleep(0.2)
            new = pd.DataFrame(out)
            if not new.empty:
                new["time"] = pd.to_datetime(new["fundingTime"], unit="ms", utc=True)
                new["fundingRate"] = new["fundingRate"].astype(float)
                new["symbol"] = sym
                new = new[["time", "fundingRate", "symbol"]]
            merged = pd.concat([old, new], ignore_index=True)
            if merged.empty:
                print(f"  ! funding {sym}: no data")
                continue
            merged["time"] = pd.to_datetime(merged["time"], utc=True)
            merged = merged.drop_duplicates("time").sort_values("time").reset_index(drop=True)
            os.makedirs(dd, exist_ok=True)
            merged.to_parquet(fpath, index=False)
            ok += 1
            print(f"  funding {sym}: {len(merged)} rows (+{len(new)} fetched) -> {merged['time'].max().date()}")
        except Exception as e:
            print(f"  ! funding fail {sym}: {repr(e)[:120]}")
    print(f"funding done: {ok}/{len(FUNDING_SYMBOLS)}")


# --------------------------------------------------------------------------- #
#  rates (FRED OECD 3M金利) — 全取得                                           #
# --------------------------------------------------------------------------- #
def refresh_rates():
    SERIES = {"USD": "IR3TIB01USM156N", "JPY": "IR3TIB01JPM156N", "EUR": "IR3TIB01EZM156N",
              "GBP": "IR3TIB01GBM156N", "AUD": "IR3TIB01AUM156N", "CAD": "IR3TIB01CAM156N",
              "CHF": "IR3TIB01CHM156N", "NZD": "IR3TIB01NZM156N"}

    def fetch(sid):
        raw = _get_bytes(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60)
        df = pd.read_csv(io.BytesIO(raw))
        df.columns = ["date", "rate"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        return df.dropna()

    series = {}
    for ccy, sid in SERIES.items():
        try:
            series[ccy] = fetch(sid).set_index("date")["rate"].resample("MS").last()
        except Exception as e:
            print(f"  ! rate {ccy}: {repr(e)[:100]}")
    if "USD" not in series:
        print("  ! rates: no USD")
        return
    us = series["USD"]
    rows = []
    for ccy, s in series.items():
        if ccy == "USD":
            continue
        m = pd.concat({"rate": s, "us_rate": us}, axis=1).dropna()
        m["ccy"] = ccy
        m["diff"] = m["rate"] - m["us_rate"]
        rows.append(m.reset_index().rename(columns={"index": "date"}))
    out = pd.concat(rows, ignore_index=True)[["date", "ccy", "rate", "us_rate", "diff"]]
    out = out.sort_values(["ccy", "date"]).reset_index(drop=True)
    os.makedirs(os.path.join(DATA, "macro"), exist_ok=True)
    out.to_parquet(os.path.join(DATA, "macro", "rates_fred.parquet"), index=False)
    print(f"rates done: {len(out)} rows -> {out['date'].max().date()}")


# --------------------------------------------------------------------------- #
#  cot (CFTC COT) — 当年(+年初は前年)を既存とマージ                          #
# --------------------------------------------------------------------------- #
COT_MARKETS = [("EURO FX", "EURUSD", +1), ("JAPANESE YEN", "USDJPY", -1),
               ("POUND STERLING", "GBPUSD", +1), ("AUSTRALIAN DOLLAR", "AUDUSD", +1),
               ("CANADIAN DOLLAR", "USDCAD", -1), ("SWISS FRANC", "USDCHF", -1),
               ("NEW ZEALAND DOLLAR", "NZDUSD", +1)]


def _col(df, *keys):
    low = {c.lower().strip(): c for c in df.columns}
    for cand in low:
        if all(k.lower() in cand for k in keys):
            return low[cand]
    return None


def _parse_cot(raw):
    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    c_mkt = _col(df, "market", "exchange")
    c_dt = _col(df, "as of date", "yyyy-mm-dd") or _col(df, "as of date", "yymmdd")
    c_oi = _col(df, "open interest", "(all)")
    c_ncl = _col(df, "noncommercial", "long", "(all)")
    c_ncs = _col(df, "noncommercial", "short", "(all)")
    if None in (c_mkt, c_dt, c_oi, c_ncl, c_ncs):
        raise RuntimeError(f"cot columns missing: {list(df.columns)[:14]}")
    name = df[c_mkt].astype(str).str.upper()
    out = []
    for key, pair, sign in COT_MARKETS:
        m = df[name.str.contains(key, regex=False)]
        if m.empty:
            continue
        d = pd.DataFrame({
            "date": pd.to_datetime(m[c_dt].astype(str), errors="coerce",
                                   format="%Y-%m-%d" if "yyyy" in c_dt.lower() else None),
            "oi": pd.to_numeric(m[c_oi], errors="coerce"),
            "ncl": pd.to_numeric(m[c_ncl], errors="coerce"),
            "ncs": pd.to_numeric(m[c_ncs], errors="coerce")})
        d = d.dropna()
        d = d[d.oi > 0]
        d["market"], d["pair"], d["sign"] = key, pair, sign
        out.append(d)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def refresh_cot():
    BASE = "https://www.cftc.gov/files/dea/history"
    nowdt = datetime.now(timezone.utc)
    years = [nowdt.year] + ([nowdt.year - 1] if nowdt.month <= 2 else [])
    new = []
    for y in years:
        url = f"{BASE}/deacot{y}.zip"
        try:
            zf = zipfile.ZipFile(io.BytesIO(_get_bytes(url)))
            txt = [n for n in zf.namelist() if n.lower().endswith(".txt")]
            new.append(_parse_cot(zf.read(txt[0])))
        except Exception as e:
            print(f"  ! cot {y}: {repr(e)[:100]}")
    path = os.path.join(DATA, "cot", "cot_fx.parquet")
    frames = []
    if os.path.exists(path):
        frames.append(pd.read_parquet(path))
    frames += [d for d in new if not d.empty]
    if not frames:
        print("  ! cot: no data")
        return
    cot = pd.concat(frames, ignore_index=True)
    cot["date"] = pd.to_datetime(cot["date"])
    cot = cot.drop_duplicates(["date", "pair"]).sort_values(["pair", "date"]).reset_index(drop=True)
    cot["net_frac"] = (cot.ncl - cot.ncs) / cot.oi
    cot["avail"] = cot["date"] + pd.Timedelta(days=6)
    os.makedirs(os.path.join(DATA, "cot"), exist_ok=True)
    cot.to_parquet(path, index=False)
    print(f"cot done: {len(cot)} rows -> {cot['date'].max().date()}")


# --------------------------------------------------------------------------- #
#  dvol (Deribit) — 全取得                                                     #
# --------------------------------------------------------------------------- #
def refresh_dvol():
    BASE = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
    now = _now_ms()
    start = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    for cur_ccy, name in [("BTC", "dvol_btc"), ("ETH", "dvol_eth")]:
        try:
            out, cur = [], start
            chunk = 365 * 86400 * 1000
            while cur < now:
                w_end = min(cur + chunk, now)
                d = _get_json(f"{BASE}?currency={cur_ccy}&start_timestamp={cur}"
                              f"&end_timestamp={w_end}&resolution=1D")
                out += d.get("result", {}).get("data", [])
                cur = w_end + 1
                time.sleep(0.2)
            if not out:
                print(f"  ! dvol {cur_ccy}: empty")
                continue
            df = pd.DataFrame(out, columns=["t", "o", "h", "l", "dvol"]).drop_duplicates("t")
            df["time"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True)
            df["dvol"] = df["dvol"].astype(float)
            df = df[["time", "dvol"]].sort_values("time").reset_index(drop=True)
            os.makedirs(os.path.join(DATA, "macro"), exist_ok=True)
            df.to_parquet(os.path.join(DATA, "macro", f"{name}.parquet"), index=False)
            print(f"  dvol {cur_ccy}: {len(df)} rows -> {df['time'].max().date()}")
        except Exception as e:
            print(f"  ! dvol {cur_ccy}: {repr(e)[:120]}")
    print("dvol done")


# --------------------------------------------------------------------------- #
def main():
    targets = [a.lower() for a in sys.argv[1:]] or ["funding", "rates", "cot", "dvol"]
    print(f"refresh targets: {targets}  -> {DATA}")
    if "funding" in targets:
        refresh_funding()
    if "rates" in targets:
        refresh_rates()
    if "cot" in targets:
        refresh_cot()
    if "dvol" in targets:
        refresh_dvol()
    print("REFRESH COMPLETE")


if __name__ == "__main__":
    main()
