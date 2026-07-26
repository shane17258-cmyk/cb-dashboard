#!/usr/bin/env python3
"""
可轉債 CB 自動資料抓取腳本
資料來源：
  1. thefew.tw - CB 市場價格（免費，10支可見）
  2. 櫃買中心 TPEx OpenAPI - CB 發行資訊（免費）
  3. 證交所 TWSE OpenAPI - 個股日成交資訊（免費）
"""
import json
import os
import re
import urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data.json")
HIST_FILE = os.path.join(SCRIPT_DIR, "history.json")

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


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  [WARN] {url}: {e}")
        return None


def fetch_thefew_cb():
    """Fetch CB data from thefew.tw (free, ~10 CBs visible without login)"""
    print("[1/3] Fetching thefew.tw CB data...")
    html = fetch_html("https://thefew.tw/cb")
    if not html:
        return []

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
    cb_list = []

    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) < 8:
            continue

        # CB code
        code_match = re.search(r"inline-block w-1/3[^>]*>\s*(\d{5})\s*<", cells[0])
        if not code_match:
            continue
        cb_code = code_match.group(1)

        # Skip login-gated rows
        if "註冊/登入後查看" in row:
            continue

        # Name
        name_match = re.search(r"inline-block w-2/3[^>]*>\s*([^\n<]+?)\s*<", cells[0])
        name = name_match.group(1).strip() if name_match else ""

        def extract_num(cell):
            m = re.search(r">([\d.]+)<", cell)
            if m:
                return float(m.group(1))
            m = re.search(r"([\d.]+)", cell)
            if m:
                return float(m.group(1))
            return 0

        def extract_pct(cell):
            m = re.search(r">([-\d.]+)%<", cell)
            if m:
                return float(m.group(1))
            m = re.search(r"([-\d.]+)%", cell)
            if m:
                return float(m.group(1))
            return 0

        cb_close = extract_num(cells[1])
        conv_value = extract_num(cells[2])
        premium = extract_pct(cells[3])
        stock_close = extract_num(cells[4])
        conv_price = extract_num(cells[5])
        converted_pct = extract_pct(cells[6])

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", cells[7])
        maturity = date_match.group(1) if date_match else ""

        cb_list.append({
            "code": cb_code,
            "name": name,
            "cb_close": cb_close,
            "conv_value": conv_value,
            "premium": premium,
            "stock_close": stock_close,
            "conv_price": conv_price,
            "converted_pct": converted_pct,
            "maturity": maturity,
            "source": "thefew.tw",
        })

    print(f"  -> {len(cb_list)} CBs with real market prices")
    return cb_list


def fetch_cb_issuance():
    """Fetch CB issuance data from TPEx"""
    print("[2/3] Fetching TPEx CB issuance data...")
    data = fetch_json(f"{TPEx_BASE}/bond_ISSBD6_data")
    if data:
        print(f"  -> {len(data)} CB issuance records")
    return data or []


def fetch_stock_prices():
    """Fetch all TWSE stock daily closing prices"""
    print("[3/3] Fetching TWSE stock prices...")
    data = fetch_json(f"{TWSE_BASE}/exchangeReport/STOCK_DAY_ALL")
    if data:
        print(f"  -> {len(data)} stock records")
    return data or []


def process_data(thefew_cb, cb_issuance, stock_prices):
    """Process and calculate statistics"""
    print("\n[Processing] Combining data sources...")

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

    # Start with thefew.tw data (real CB prices)
    all_cb = {cb["code"]: cb for cb in thefew_cb}

    # Add TPEx issuance data for CBs not in thefew
    for cb in cb_issuance:
        code = cb.get("IssuerCode", "")
        if code in all_cb:
            continue  # Already have real price

        conv_price_str = cb.get("Conversion/ExchangePriceAtIssuance", "0")
        try:
            conv_price = float(conv_price_str)
        except:
            conv_price = 0

        stock_price = stock_map.get(code, 0)

        if conv_price > 0 and stock_price > 0:
            conv_value = round((stock_price / conv_price) * 100, 1)
        else:
            conv_value = 0

        premium = round(conv_value - 100, 1) if conv_value > 0 else 0

        all_cb[code] = {
            "code": code,
            "name": cb.get("IssuerName", ""),
            "cb_close": 0,  # No real market price
            "conv_value": conv_value,
            "premium": premium,
            "stock_close": stock_price,
            "conv_price": conv_price,
            "converted_pct": 0,
            "maturity": "",
            "source": "TPEx (calculated)",
        }

    cb_list = list(all_cb.values())
    valid = [c for c in cb_list if c["cb_close"] > 0 or c["conv_value"] > 0]

    # Price distribution (using CB close price where available, else conversion value)
    ranges = {
        "noBid": {"count": 0, "cumPct": "0%"},
        "lt95": {"count": 0, "cumPct": "0%"},
        "95to100": {"count": 0, "cumPct": "0%"},
        "100to105": {"count": 0, "cumPct": "0%"},
        "105to110": {"count": 0, "cumPct": "0%"},
        "110to120": {"count": 0, "cumPct": "0%"},
        "gte120": {"count": 0, "cumPct": "0%"},
    }

    # Use CB close price for distribution
    for cb in cb_list:
        p = cb["cb_close"]
        if p == 0:
            ranges["noBid"]["count"] += 1
        elif p < 95:
            ranges["lt95"]["count"] += 1
        elif p < 100:
            ranges["95to100"]["count"] += 1
        elif p < 105:
            ranges["100to105"]["count"] += 1
        elif p < 110:
            ranges["105to110"]["count"] += 1
        elif p < 120:
            ranges["110to120"]["count"] += 1
        else:
            ranges["gte120"]["count"] += 1

    total = sum(r["count"] for r in ranges.values())
    cum = 0
    for key in ["noBid", "lt95", "95to100", "100to105", "105to110", "110to120", "gte120"]:
        cum += ranges[key]["count"]
        ranges[key]["cumPct"] = f"{round(cum / total * 100, 1)}%" if total > 0 else "0%"

    # Statistics
    closes_with_price = [c["cb_close"] for c in cb_list if c["cb_close"] > 0]
    premiums = [c["premium"] for c in valid if c["premium"] != 0]
    conv_values = [c["conv_value"] for c in valid if c["conv_value"] > 0]

    avg_close = round(sum(closes_with_price) / len(closes_with_price), 1) if closes_with_price else 0
    avg_premium = round(sum(premiums) / len(premiums), 1) if premiums else 0
    avg_cv = round(sum(conv_values) / len(conv_values), 1) if conv_values else 0

    sorted_c = sorted(closes_with_price) if closes_with_price else [0]
    n = len(sorted_c)
    pr75 = sorted_c[int(n * 0.75)] if n > 0 else 0
    pr90 = sorted_c[int(n * 0.90)] if n > 0 else 0

    gt100 = [c for c in valid if c["conv_value"] > 100]
    avg_prem_gt100 = round(sum(c["premium"] for c in gt100) / len(gt100), 1) if gt100 else 0

    data = {
        "dataDate": today,
        "validSamples": len(valid),
        "sampleWithPrice": len(closes_with_price),
        "dataSource": "thefew.tw + TPEx + TWSE",
        "totalCB": total,
        "bidPriceRanges": ranges,
        "avgBidPrice": avg_close,
        "pr75": pr75,
        "pr90": pr90,
        "avgConversionValue": avg_cv,
        "avgConversionPremium": avg_premium,
        "conversionValueGt100AvgPremium": avg_prem_gt100,
        "conversionValueGte100": len([v for v in conv_values if v >= 100]),
        "conversionValueGte120": len([v for v in conv_values if v >= 120]),
        "conversionPremiumGt0": len([p for p in premiums if p > 0]),
        "conversionPremiumGte50": len([p for p in premiums if p >= 50]),
        "conversionPremiumGte100": len([p for p in premiums if p >= 100]),
        "cbTop20": sorted(
            [{"code": c["code"], "name": c["name"], "cb_close": c["cb_close"],
              "conv_value": c["conv_value"], "premium": c["premium"],
              "stock_close": c["stock_close"], "conv_price": c["conv_price"],
              "source": c["source"]}
             for c in valid],
            key=lambda x: x["cb_close"] if x["cb_close"] > 0 else x["conv_value"],
            reverse=True
        )[:20],
    }

    # Load and update history
    history = []
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            pass

    new_entry = {
        "date": today,
        "avgBidPrice": avg_close,
        "totalCB": total,
        "avgConversionPremium": avg_premium,
    }
    history = [h for h in history if h["date"] != today]
    history.append(new_entry)
    history = history[-60:]
    data["history"] = history

    with open(HIST_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"  Total CB: {total}, With real price: {len(closes_with_price)}")
    print(f"  Avg CB Close: {avg_close}, Avg Premium: {avg_premium}%")
    print(f"  PR75: {pr75}, PR90: {pr90}")

    return data


def main():
    print("=" * 50)
    print("  CB Auto Data Fetch")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    thefew = fetch_thefew_cb()
    cb_issuance = fetch_cb_issuance()
    stocks = fetch_stock_prices()
    data = process_data(thefew, cb_issuance, stocks)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Saved to {DATA_FILE}")


if __name__ == "__main__":
    main()
