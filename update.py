#!/usr/bin/env python3
"""
可轉債 CB 數據更新腳本
用法: python update.py
功能: 從 XQ 或手動輸入更新 data.json
"""
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data.json")

def load_existing():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已更新 {DATA_FILE}")

def update_manual():
    today = datetime.now().strftime("%Y/%m/%d")
    print(f"\n=== 可轉債數據更新 ({today}) ===\n")
    print("請從 XQ 或其他來源輸入今日數據：\n")

    data = load_existing()

    data["dataDate"] = input(f"資料日期 [{today}]: ").strip() or today
    data["validSamples"] = int(input(f"有效樣本數 [{data['validSamples']}]: ").strip() or data["validSamples"])
    data["dataSource"] = input(f"資料來源 [{data['dataSource']}]: ").strip() or data["dataSource"]
    data["totalCB"] = int(input(f"CB 總數 [{data['totalCB']}]: ").strip() or data["totalCB"])

    r = data["bidPriceRanges"]
    print("\n--- CB 委買價格區間 ---")
    r["noBid"]["count"] = int(input(f"無委買 [{r['noBid']['count']}]: ").strip() or r["noBid"]["count"])
    r["lt95"]["count"] = int(input(f"<95 [{r['lt95']['count']}]: ").strip() or r["lt95"]["count"])
    r["95to100"]["count"] = int(input(f"95~100 [{r['95to100']['count']}]: ").strip() or r["95to100"]["count"])
    r["100to105"]["count"] = int(input(f"100~105 [{r['100to105']['count']}]: ").strip() or r["100to105"]["count"])
    r["105to110"]["count"] = int(input(f"105~110 [{r['105to110']['count']}]: ").strip() or r["105to110"]["count"])
    r["110to120"]["count"] = int(input(f"110~120 [{r['110to120']['count']}]: ").strip() or r["110to120"]["count"])
    r["gte120"]["count"] = int(input(f">=120 [{r['gte120']['count']}]: ").strip() or r["gte120"]["count"])

    # recalc cumulative percentages
    total = sum(v["count"] for v in r.values())
    cum = 0
    for k in ["noBid", "lt95", "95to100", "100to105", "105to110", "110to120", "gte120"]:
        cum += r[k]["count"]
        r[k]["cumPct"] = f"{round(cum / total * 100, 1)}%"

    print("\n--- 其他指標 ---")
    data["avgBidPrice"] = float(input(f"CB 委買平均價 [{data['avgBidPrice']}]: ").strip() or data["avgBidPrice"])
    data["pr75"] = float(input(f"PR75 最高價 [{data['pr75']}]: ").strip() or data["pr75"])
    data["pr90"] = float(input(f"PR90 最高價 [{data['pr90']}]: ").strip() or data["pr90"])
    data["avgConversionValue"] = float(input(f"CB 平均轉換價值 [{data['avgConversionValue']}]: ").strip() or data["avgConversionValue"])
    data["avgConversionPremium"] = float(input(f"CB 平均轉換溢價率 [{data['avgConversionPremium']}]: ").strip() or data["avgConversionPremium"])
    data["conversionValueGt100AvgPremium"] = float(input(f"轉換價值>100 平均溢價率 [{data['conversionValueGt100AvgPremium']}]: ").strip() or data["conversionValueGt100AvgPremium"])

    data["conversionValueGte100"] = int(input(f"轉換價值>=100 數量 [{data['conversionValueGte100']}]: ").strip() or data["conversionValueGte100"])
    data["conversionValueGte120"] = int(input(f"轉換價值>=120 數量 [{data['conversionValueGte120']}]: ").strip() or data["conversionValueGte120"])
    data["conversionPremiumGt0"] = int(input(f"溢價率>0% 數量 [{data['conversionPremiumGt0']}]: ").strip() or data["conversionPremiumGt0"])
    data["conversionPremiumGte50"] = int(input(f"溢價率>=50% 數量 [{data['conversionPremiumGte50']}]: ").strip() or data["conversionPremiumGte50"])
    data["conversionPremiumGte100"] = int(input(f"溢價率>=100% 數量 [{data['conversionPremiumGte100']}]: ").strip() or data["conversionPremiumGte100"])

    # update history
    new_entry = {
        "date": data["dataDate"],
        "avgBidPrice": data["avgBidPrice"],
        "totalCB": data["totalCB"],
        "avgConversionPremium": data["avgConversionPremium"]
    }
    data["history"] = data.get("history", [])
    # remove duplicate date
    data["history"] = [h for h in data["history"] if h["date"] != data["dataDate"]]
    data["history"].append(new_entry)
    # keep last 30 days
    data["history"] = data["history"][-30:]

    save_data(data)
    print("\n更新完成！")

if __name__ == "__main__":
    update_manual()
