# WS TCG Crawler (Weiss Schwarz 卡表爬蟲)

## 📥 安裝與設定

1.  **複製專案到本地**

    ```bash
    git clone https://github.com/U-CLIMAX/ws-tcg-crawler
    cd ws-tcg-crawler
    ```

2.  **安裝相依套件**

    ```bash
    uv sync
    ```

3.  **安裝瀏覽器核心**

    ```bash
    uv run playwright install chromium
    ```

## 🚀 使用方法

本工具只需一個參數：**系列名稱**。

須確保名稱有出現在 https://ws-tcg.com/cardlist/

![cardlist](/image/cardlist.png)

### 執行爬蟲

請在專案根目錄下執行：

```bash
uv run src/main.py -s "系列名稱"
```

**範例：**

```bash
uv run src/main.py -s "甘神さんちの縁結び"
```

### 互動式選擇流程

1.  程式會啟動瀏覽器（headless）並前往 WS 官網搜尋該系列。
2.  當找到系列後，終端機將顯示該系列下所有的 **補充包/產品** 選單。
3.  **使用鍵盤 `↑` `↓` 移動，按下 `Enter` 確認選擇**。

```text
? 請選擇要爬取的產品 (上下鍵移動，Enter 確認):
 > すべて
   ヴァイスサイド
   [TD]甘神さんちの縁結び
   甘神さんちの縁結び
```

4.  程式將自動開始爬取卡片資料、下載圖片，並儲存結果。

## 📂 輸出結構

每次執行爬蟲，都會在 `data/` 目錄下產生一個以 **當下時間** 命名的資料夾，確保資料隔離。

```text
ws-crawler/
├── data/
│   └── 20251123_163000/           # [時間戳資料夾]
│       ├── scraper.log            # 完整的執行日誌 (Loguru)
│       ├── card-data/             # JSON 數據存放區
│       │   └── gmk-td.json        # 產品 ID 命名的 JSON 檔
│       └── card-images/           # 圖片存放區
│           └── gmk-td/            # 依產品分類的圖片資料夾
│               ├── gmk-w101-001.png
│               └── ...
└── src/
    ├── main.py
    ├── models.py
    ├── parser.py
    └── downloader.py
```

### JSON 資料範例

輸出的 JSON 格式如下，包含完整的卡片數值與效果文：

```json
{
  "GMK/W101-001": {
    "name": "巫女のあそび",
    "product_name": "甘神さんちの縁結び",
    "type": "角色卡",
    "level": 0,
    "power": 1500,
    "cost": 0,
    "soul": 1,
    "trigger_soul_count": 0,
    "trait": ["神", "巫女"],
    "color": "红色",
    "effect": "【永】你的回合中...",
    "all_cards": [
      {
        "id": "GMK/W101-001",
        "rarity": "RR"
      },
      {
        "id": "GMK/W101-001SP",
        "rarity": "SP"
      }
    ]
  }
}
```

## 🏗️ 專案架構

  * **`src/main.py`**: 程式入口。負責 Playwright 導航、互動選單邏輯、以及流程控制。
  * **`src/models.py`**: 定義 `CardData` 資料結構 (Pydantic)，確保資料欄位正確。
  * **`src/parser.py`**: 負責使用 `BeautifulSoup` 解析 HTML 表格，清洗文字與替換圖示路徑。
  * **`src/downloader.py`**: 負責使用 `httpx` 進行非同步圖片下載。

## 📝 常見問題

**Q: 執行時出現 `playwright not installed` 錯誤？**
A: 請確認您已執行 `uv run playwright install chromium`。

**Q: 找不到系列？**
A: 請確保 `-s` 參數後的系列名稱與 WS 官網上的「タイトル (Title)」完全一致（建議直接從官網複製日文名稱）。
