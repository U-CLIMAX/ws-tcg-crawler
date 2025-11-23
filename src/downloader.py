import asyncio
from pathlib import Path

import httpx
from loguru import logger


async def download_image(
    client: httpx.AsyncClient, url: str, path: Path, semaphore: asyncio.Semaphore
):
    """下載單張圖片，使用 Semaphore 限制最大併發數"""
    if path.exists():
        return  # 如果檔案已存在則跳過

    async with semaphore:
        try:
            # 去除 url 中的換行符號
            clean_url = url.strip().replace("\n", "")
            resp = await client.get(clean_url)
            resp.raise_for_status()

            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            logger.error(f"下載失敗 {url}: {e}")


async def batch_download_images(
    tasks: list[tuple[str, Path]], max_concurrency: int = 10
):
    """
    批量下載圖片
    tasks: List[(url, save_path)]
    """
    if not tasks:
        return

    logger.info(f"開始下載 {len(tasks)} 張圖片...")

    semaphore = asyncio.Semaphore(max_concurrency)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        download_tasks = [
            download_image(client, url, path, semaphore) for url, path in tasks
        ]
        await asyncio.gather(*download_tasks)

    logger.info("所有圖片下載任務完成")
