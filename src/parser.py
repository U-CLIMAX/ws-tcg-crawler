import re
from pathlib import Path

from bs4 import Tag

# 常數映射
COLOR_MAP = {
    "yellow.gif": "黄色",
    "red.gif": "红色",
    "green.gif": "绿色",
    "blue.gif": "蓝色",
}
TYPE_MAP = {"キャラ": "角色卡", "クライマックス": "高潮卡", "イベント": "事件卡"}
BASE_URL = "https://ws-tcg.com"


def parse_card_row(row: Tag) -> dict | None:
    """解析單個 <tr> 標籤，提取卡片原始數據"""
    h4 = row.find("h4")
    if not h4:
        return None

    try:
        spans = h4.select("span.highlight_target")
        if len(spans) < 2:
            return None

        # 1. 基礎資訊
        name = spans[0].text.strip().replace("　", " ")
        full_card_no = spans[1].text.strip()
        key = re.sub(r"[A-Za-z]+[+]?$", "", full_card_no)

        # 2. 產品名稱 (原始與清洗後)
        product_name_raw = ""
        product_name = "-"
        if a_tag := h4.find("a"):
            product_name_raw = str(a_tag.next_sibling).strip()
            product_name = (
                product_name_raw.lstrip("-").strip().replace("　", " ") or "-"
            )

        # 3. 圖片連結
        img_tag = row.select_one("th a img")
        image_url = f"{BASE_URL}{img_tag['src'].strip()}" if img_tag else ""

        # 4. 表格內屬性解析
        temp_data = {}
        for span in row.select("td span.unit"):
            text = span.text.strip()
            if text.startswith("種類："):
                temp_data["type"] = text.replace("種類：", "").strip()
            elif text.startswith("レベル："):
                temp_data["level"] = text.replace("レベル：", "").strip()
            elif text.startswith("パワー："):
                temp_data["power"] = text.replace("パワー：", "").strip()
            elif text.startswith("コスト："):
                temp_data["cost"] = text.replace("コスト：", "").strip()
            elif text.startswith("レアリティ："):
                temp_data["rarity"] = text.replace("レアリティ：", "").strip()
            elif text.startswith("特徴："):
                temp_data["trait"] = text.replace("特徴：", "").strip()
            elif "色：" in str(span) and (img := span.find("img")):
                temp_data["color_img"] = Path(img["src"]).name
            elif "ソウル：" in str(span):
                temp_data["soul_count"] = str(span).count("soul.gif")
            elif "トリガー：" in str(span):
                temp_data["trigger_soul_count"] = str(span).count("soul.gif")

        # 5. 數據清洗與轉換
        level = (
            int(temp_data.get("level", "-"))
            if temp_data.get("level", "-").isdigit()
            else "-"
        )
        power = (
            int(temp_data.get("power", "-"))
            if temp_data.get("power", "-").isdigit()
            else "-"
        )
        cost = (
            int(temp_data.get("cost", "-"))
            if temp_data.get("cost", "-").isdigit()
            else "-"
        )

        traits_text = temp_data.get("trait", "-")
        trait = (
            [t.strip() for t in traits_text.split("・")]
            if traits_text not in ["-", "－"]
            else "-"
        )

        color = COLOR_MAP.get(temp_data.get("color_img"), "-")

        # 6. 效果文處理
        effect = ""
        if effect_tag := row.select_one("td > span.highlight_target"):
            effect_text = effect_tag.decode_contents().strip().replace("\n", "")
            old_path = "/wordpress/wp-content/images/cardlist/_partimages"
            new_path = "/effect-icons"
            effect_text = effect_text.replace(old_path, new_path).replace(
                ".gif", ".webp"
            )
            effect = (
                effect_text.replace("　", " ") if effect_text not in ["-", "－"] else ""
            )

        return {
            "key": key,
            "name": name,
            "full_card_no": full_card_no,
            "rarity": temp_data.get("rarity", "-"),
            "product_name_raw": product_name_raw,  # 這是給 main.py 判斷邏輯用的
            "product_name": product_name,  # <--- 這是要存入 JSON 的
            "image_url": image_url,
            "type": TYPE_MAP.get(temp_data.get("type"), "-"),
            "level": level,
            "power": power,
            "cost": cost,
            "soul": temp_data.get("soul_count", 0) or "-",
            "trigger_soul_count": temp_data.get("trigger_soul_count", 0),
            "trait": trait,
            "color": color,
            "effect": effect,
        }

    except Exception:
        return None
