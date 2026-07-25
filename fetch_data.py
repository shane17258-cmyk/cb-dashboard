#!/usr/bin/env python3
"""
可轉債 CB 自動資料抓取腳本
資料來源：
  1. 櫃買中心 TPEx OpenAPI - CB 發行資訊 (免費)
  2. 證交所 TWSE OpenAPI - 個股日成交資訊 (免費)
  3. 自動計算轉換價值 & 溢價率

注意：免費 API 無法直接取得 CB 市場價格，
     此腳本使用「轉換價值」作為分析基礎。
"""
import json
import os
import urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data.json")

TPEx_BASE = "https://www.tpex.org.tw/openapi/v1"
TWSE_BASE = "https://openapi.twse.com.tw/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] {url}: {e}")
        return None


def fetch_cb_issuance():
    """Fetch all CB (海外+國內) issuance data from TPEx"""
    print("[1/3] Fetching CB issuance data...")
    data = fetch_json(f"{TPEx_BASE}/bond_ISSBD6_data")
    if data:
        print(f"  -> {len(data)} CB records")
    return data or []


def fetch_stock_prices():
    """Fetch all TWSE stock daily closing prices"""
    print("[2/3] Fetching TWSE stock prices...")
    data = fetch_json(f"{TWSE_BASE}/exchangeReport/STOCK_DAY_ALL")
    if data:
        print(f"  -> {len(data)} stock records")
    return data or []


def process_data(cb_issuance, stock_prices):
    """Process and calculate statistics"""
    print("[3/3] Processing data...")

    today = datetime.now().strftime("%Y/%m/%d")

    # Build stock price lookup
    stock_map = {}
    for s in stock_prices:
        code = s.get("Code", "") or s.get("StockCode", "")
        close = s.get("ClosingPrice", "")
        if code and close:
            try:
                stock_map[code] = float(close)
            except (ValueError, TypeError):
                pass

    # Process each CB
    cb_list = []
    for cb in cb_issuance:
        issuer = cb.get("IssuerCode", "")
        conv_price_str = cb.get("Conversion/ExchangePriceAtIssuance", "0")
        try:
            conv_price = float(conv_price_str)
        except:
            conv_price = 0

        stock_price = stock_map.get(issuer, 0)

        # Conversion value = (stock_price / conversion_price) * 100
        if conv_price > 0 and stock_price > 0:
            conv_value = round((stock_price / conv_price) * 100, 1)
        else:
            conv_value = 0

        # Premium = conversion_value - 100
        premium = round(conv_value - 100, 1) if conv_value > 0 else 0

        cb_list.append({
            "code": issuer,
            "name": cb.get("IssuerName", ""),
            "series": cb.get("SeriesNumber", ""),
            "conv_price": conv_price,
            "stock_price": stock_price,
            "conv_value": conv_value,
            "premium": premium,
            "issue_amount": cb.get("IssueAmount", "0"),
            "short_name": cb.get("ShortName", ""),
        })

    # Filter valid records
    valid = [c for c in cb_list if c["conv_value"] > 0]
    all_values = [c["conv_value"] for c in valid]

    # Price range distribution (using conversion value as proxy)
    ranges = {
        "noBid": {"count": len([c for c in cb_list if c["conv_value"] == 0]), "cumPct": "0%"},
        "lt95": {"count": 0, "cumPct": "0%"},
        "95to100": {"count": 0, "cumPct": "0%"},
        "100to105": {"count": 0, "cumPct": "0%"},
        "105to110": {"count": 0, "cumPct": "0%"},
        "110to120": {"count": 0, "cumPct": "0%"},
        "gte120": {"count": 0, "cumPct": "0%"},
    }

    for v in all_values:
        if v < 95:
            ranges["lt95"]["count"] += 1
        elif v < 100:
            ranges["95to100"]["count"] += 1
        elif v < 105:
            ranges["100to105"]["count"] += 1
        elif v < 110:
            ranges["105to110"]["count"] += 1
        elif v < 120:
            ranges["110to120"]["count"] += 1
        else:
            ranges["gte120"]["count"] += 1

    total = sum(r["count"] for r in ranges.values())
    cum = 0
    for key in ["noBid", "lt95", "95to100", "100to105", "105to110", "110to120", "gte120"]:
        cum += ranges[key]["count"]
        ranges[key]["cumPct"] = f"{round(cum / total * 100, 1)}%" if total > 0 else "0%"

    # Statistics
    avg_cv = round(sum(all_values) / len(all_values), 1) if all_values else 0
    premiums = [c["premium"] for c in valid]
    avg_premium = round(sum(premiums) / len(premiums), 1) if premiums else 0

    sorted_v = sorted(all_values)
    n = len(sorted_v)
    pr75 = sorted_v[int(n * 0.75)] if n > 0 else 0
    pr90 = sorted_v[int(n * 0.90)] if n > 0 else 0

    gt100 = [c for c in valid if c["conv_value"] > 100]
    avg_prem_gt100 = round(sum(c["premium"] for c in gt100) / len(gt100), 1) if gt100 else 0

    data = {
        "dataDate": today,
        "validSamples": len(valid),
        "dataSource": "TPEx+TWSE (轉換價值)",
        "totalCB": total,
        "bidPriceRanges": ranges,
        "avgBidPrice": avg_cv,
        "pr75": pr75,
        "pr90": pr90,
        "avgConversionValue": avg_cv,
        "avgConversionPremium": avg_premium,
        "conversionValueGt100AvgPremium": avg_prem_gt100,
        "conversionValueGte100": len([v for v in all_values if v >= 100]),
        "conversionValueGte120": len([v for v in all_values if v >= 120]),
        "conversionPremiumGt0": len([p for p in premiums if p > 0]),
        "conversionPremiumGte50": len([p for p in premiums if p >= 50]),
        "conversionPremiumGte100": len([p for p in premiums if p >= 100]),
        "cbTop20": sorted(cb_list, key=lambda x: x["conv_value"], reverse=True)[:20],
    }

    # Load history
    history = []
    hist_file = os.path.join(SCRIPT_DIR, "history.json")
    if os.path.exists(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            pass

    new_entry = {
        "date": today,
        "avgBidPrice": avg_cv,
        "totalCB": total,
        "avgConversionPremium": avg_premium,
    }
    history = [h for h in history if h["date"] != today]
    history.append(new_entry)
    history = history[-60:]
    data["history"] = history

    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"  Total CB: {total}, Valid: {len(valid)}")
    print(f"  Avg CV: {avg_cv}, Avg Premium: {avg_premium}%")
    print(f"  PR75: {pr75}, PR90: {pr90}")

    return data


def main():
    print("=" * 50)
    print("  CB Auto Data Fetch")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    cb = fetch_cb_issuance()
    stocks = fetch_stock_prices()
    data = process_data(cb, stocks)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Saved to {DATA_FILE}")


if __name__ == "__main__":
    main()
