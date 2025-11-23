import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import questionary
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright

from downloader import batch_download_images
from models import CardData, CardVersion
from parser import BASE_URL, parse_card_row

# 設定專案根目錄
ROOT_DIR = Path(__file__).resolve().parent.parent


class WsScraper:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.data_dir = run_dir / "card-data"
        self.img_dir = run_dir / "card-images"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.img_dir.mkdir(parents=True, exist_ok=True)

        self.products_data = {}
        self.download_queue = []
        self.product_prefixes = set()

        log_file = self.run_dir / "scraper.log"
        logger.add(
            log_file,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8",
            rotation="10 MB",
        )
        logger.info(f"初始化完成，本次結果將存於: {self.run_dir}")

    def determine_product_id(
        self, card_key: str, product_name_raw: str, rarity: str
    ) -> str:
        base_id = card_key.split("-")[0].replace("/", "-")
        self.product_prefixes.add(base_id.split("-")[0])

        base_id_lower = base_id.lower()
        name_upper = product_name_raw.upper()
        rarity_upper = rarity.upper()

        if "PR" in name_upper or rarity_upper == "PR":
            return f"{base_id_lower}-pr"
        if "TD" in name_upper or rarity_upper == "TD":
            return f"{base_id_lower}-td"
        return base_id_lower

    async def scrape(self, series_name: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info(f"正在導航至 WS 官網並搜尋系列: {series_name}")
            CARDLIST_URL = f"{BASE_URL}/cardlist/"

            try:
                await page.goto(CARDLIST_URL, timeout=60000)

                # 1. 點擊系列
                series_link = page.locator(
                    f"#titleNumberList a:text-is('{series_name}')"
                ).first
                if await series_link.count() == 0:
                    logger.error(f"找不到系列: {series_name}，請確認名稱是否完全正確。")
                    return
                await series_link.click()

                # 2. 等待產品下拉選單載入
                select_selector = "#prcard_filter_work_title"
                await page.wait_for_selector(select_selector, state="visible")

                # 3. 抓取所有產品選項
                logger.info("正在讀取產品列表...")
                # 獲取所有 <option> 的文字內容
                options = await page.locator(
                    f"{select_selector} option"
                ).all_inner_texts()
                # 過濾掉空白選項
                options = [opt.strip() for opt in options if opt.strip()]

                if not options:
                    logger.error("該系列下沒有找到任何產品選項。")
                    return

                # 4. 顯示互動式選單
                # 使用者在終端機用上下鍵選擇
                selected_product_name = await questionary.select(
                    "請選擇要爬取的產品 (Enter 確認):", choices=options
                ).ask_async()

                if not selected_product_name:
                    logger.warning("使用者取消選擇，程式結束。")
                    return

                logger.info(f"使用者選擇了: {selected_product_name}")

                # 5. 在網頁上選擇該選項
                # 使用 label 選擇，對應我們剛剛抓到的文字
                await page.locator(select_selector).select_option(
                    label=selected_product_name
                )

                # 6. 等待搜尋結果表格出現
                await page.locator(".search-result-table tbody tr").first.wait_for(
                    state="visible", timeout=15000
                )

                result_text = await page.locator(
                    "#searchResults .center"
                ).text_content()
                if "件該当しました" not in result_text:
                    logger.warning("該產品下未找到任何卡片。")
                    return

                # 按照分頁爬取
                current_page = 1
                while True:
                    logger.info(f"正在處理第 {current_page} 頁...")

                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_load_state("networkidle")

                    content = await page.inner_html(".search-result-table")
                    soup = BeautifulSoup(content, "lxml")
                    rows = soup.select("tbody tr")

                    for row in rows:
                        raw_data = parse_card_row(row)
                        if not raw_data:
                            continue

                        pid = self.determine_product_id(
                            raw_data["key"],
                            raw_data["product_name_raw"],
                            raw_data["rarity"],
                        )

                        if pid not in self.products_data:
                            self.products_data[pid] = {"cards": {}}

                        key = raw_data["key"]
                        product_store = self.products_data[pid]["cards"]
                        version_info = CardVersion(
                            id=raw_data["full_card_no"], rarity=raw_data["rarity"]
                        )

                        if key in product_store:
                            product_store[key].all_cards.append(version_info)
                        else:
                            card = CardData(**raw_data)
                            card.all_cards.append(version_info)
                            product_store[key] = card

                        if raw_data["image_url"]:
                            img_filename = (
                                f"{raw_data['full_card_no'].replace('/', '-')}.png"
                            )
                            save_path = self.img_dir / pid / img_filename
                            self.download_queue.append(
                                (raw_data["image_url"], save_path)
                            )

                    next_link = page.locator(".pager span.next a")
                    if await next_link.count() > 0:
                        await next_link.first.click()
                        await page.locator(
                            ".search-result-table tbody tr"
                        ).first.wait_for()
                        current_page += 1
                    else:
                        logger.info("已到達最後一頁。")
                        break

            except Exception as e:
                logger.error(f"爬蟲發生錯誤: {e}")
                raise e
            finally:
                await browser.close()

    async def run(self, series: str):
        await self.scrape(series)

        if self.download_queue:
            await batch_download_images(self.download_queue)

        self.save_results()

    def save_results(self):
        for pid, data in self.products_data.items():
            output_path = self.data_dir / f"{pid}.json"
            json_data = {
                k: v.model_dump(by_alias=True, exclude_none=True)
                for k, v in data["cards"].items()
            }
            logger.info(f"寫入 JSON: {output_path} (共 {len(json_data)} 張)")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

        if self.product_prefixes:
            logger.info(f"本次偵測到的前綴: {sorted(list(self.product_prefixes))}")


async def main():
    parser = argparse.ArgumentParser(description="WS Crawler")
    parser.add_argument(
        "-s", "--series", required=True, help="系列名 (例如: 甘神さんちの縁結び)"
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = ROOT_DIR / "data" / timestamp

    scraper = WsScraper(run_dir=run_output_dir)

    await scraper.run(args.series)


if __name__ == "__main__":
    asyncio.run(main())
