# 可轉債 CB Dashboard

每日更新的可轉債投資資訊儀表板，包含委買價格區間分佈、轉換價值、溢價率等關鍵指標。

## 網站

🔗 **https://shane17258-cmyk.github.io/**

## 功能

- CB 委買價格區間長條圖
- 轉換價值 & 溢價率統計
- 歷史走勢圖表
- 每日手動更新資料

## 更新資料

### 方法一：手動更新

1. 執行更新腳本：

```bash
python update.py
```

2. 依提示輸入今日數據（可從 XQ 取得）

### 方法二：直接編輯 data.json

修改 `data.json` 中的數值即可。

## 檔案結構

```
cb-dashboard/
├── index.html          # 主頁面
├── data.json           # 資料檔
├── update.py           # 資料更新腳本
├── css/
│   └── styles.css      # 樣式
└── js/
    └── app.js          # 程式邏輯
```

## 資料來源

- XQ 全球贏家
- 櫃買中心公開資訊
