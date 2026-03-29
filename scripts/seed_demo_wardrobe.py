import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4
from random import randint, choice

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import WardrobeDatabase

STYLES = ["休闲", "商务", "运动", "正式"]
COLORS = ["黑色", "白色", "灰色", "藏青色", "卡其色", "红色", "蓝色"]


def _ensure_category(cursor, parent_id: Optional[int], name: str, level: int) -> int:
    cursor.execute(
        "INSERT OR IGNORE INTO categories (parent_id, name, level) VALUES (?, ?, ?)",
        (parent_id, name, level),
    )
    cursor.execute(
        "SELECT id FROM categories WHERE parent_id IS ? AND name = ? AND level = ?",
        (parent_id, name, level),
    )
    row = cursor.fetchone()
    return int(row["id"])


def _ensure_brand(cursor, name: str) -> int:
    cursor.execute("INSERT OR IGNORE INTO brands (name, is_preset) VALUES (?, 0)", (name,))
    cursor.execute("SELECT id FROM brands WHERE name = ?", (name,))
    row = cursor.fetchone()
    return int(row["id"])


def _clear_seed_data(cursor):
    cursor.execute("SELECT id FROM products WHERE platform = 'Seed'")
    ids = [int(r["id"]) for r in cursor.fetchall()]
    if not ids:
        return
    placeholders = ",".join(["?"] * len(ids))
    cursor.execute(f"DELETE FROM product_skus WHERE product_id IN ({placeholders})", ids)
    cursor.execute(f"DELETE FROM products WHERE id IN ({placeholders})", ids)


def _build_seed_items(category_ids: Dict[str, int], brand_names: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {"title": "轻薄针织开衫", "category": "针织衫", "brand": "Uniqlo", "price": 199, "color": "米白", "size": "M", "seasons": ["春", "秋"], "style": "休闲", "tags": ["透气"]},
        {"title": "纯棉圆领T恤", "category": "T恤", "brand": "H&M", "price": 79, "color": "白色", "size": "L", "seasons": ["春", "夏"], "style": "休闲", "tags": ["透气", "防晒"]},
        {"title": "商务长袖衬衫", "category": "衬衫", "brand": "ZARA", "price": 159, "color": "浅蓝", "size": "M", "seasons": ["春", "秋", "冬"], "style": "商务", "tags": ["抗皱"]},
        {"title": "速干运动背心", "category": "背心", "brand": "Nike", "price": 129, "color": "黑色", "size": "L", "seasons": ["夏"], "style": "运动", "tags": ["速干", "透气"]},
        {"title": "连帽卫衣", "category": "卫衣", "brand": "Adidas", "price": 299, "color": "灰色", "size": "XL", "seasons": ["秋", "冬", "春"], "style": "运动", "tags": ["保暖"]},
        {"title": "修身牛仔裤", "category": "牛仔裤", "brand": "GU", "price": 199, "color": "深蓝", "size": "L", "seasons": ["春", "秋", "冬"], "style": "休闲", "tags": ["抗皱"]},
        {"title": "轻便短裤", "category": "短裤", "brand": "ANTA", "price": 99, "color": "卡其", "size": "M", "seasons": ["夏"], "style": "运动", "tags": ["速干"]},
        {"title": "直筒休闲裤", "category": "休闲裤", "brand": "Li-Ning", "price": 169, "color": "黑色", "size": "L", "seasons": ["春", "秋"], "style": "休闲", "tags": ["抗皱"]},
        {"title": "百褶短裙", "category": "短裙", "brand": "ZARA", "price": 139, "color": "藏青", "size": "S", "seasons": ["春", "夏"], "style": "休闲", "tags": ["透气"]},
        {"title": "针织半身裙", "category": "半身裙", "brand": "H&M", "price": 119, "color": "驼色", "size": "M", "seasons": ["秋", "冬"], "style": "正式", "tags": ["保暖"]},
        {"title": "轻薄夹克", "category": "夹克", "brand": "Uniqlo", "price": 399, "color": "军绿", "size": "L", "seasons": ["春", "秋"], "style": "休闲", "tags": ["防水"]},
        {"title": "经典风衣", "category": "风衣", "brand": "ZARA", "price": 599, "color": "卡其", "size": "M", "seasons": ["春", "秋"], "style": "商务", "tags": ["防水", "抗皱"]},
        {"title": "保暖羽绒服", "category": "羽绒服", "brand": "Adidas", "price": 899, "color": "黑色", "size": "L", "seasons": ["冬"], "style": "运动", "tags": ["保暖", "防水"]},
        {"title": "修身西装外套", "category": "西装外套", "brand": "GU", "price": 499, "color": "深灰", "size": "M", "seasons": ["春", "秋", "冬"], "style": "正式", "tags": ["抗皱"]},
        {"title": "抓绒卫衣外套", "category": "卫衣外套", "brand": "ANTA", "price": 269, "color": "浅灰", "size": "L", "seasons": ["秋", "冬"], "style": "运动", "tags": ["保暖"]},
        {"title": "碎花连衣裙", "category": "碎花裙", "brand": "H&M", "price": 229, "color": "红色", "size": "M", "seasons": ["春", "夏"], "style": "休闲", "tags": ["透气"]},
        {"title": "衬衫连衣裙", "category": "衬衫裙", "brand": "ZARA", "price": 299, "color": "白色", "size": "S", "seasons": ["春", "夏", "秋"], "style": "商务", "tags": ["抗皱"]},
        {"title": "针织连衣裙", "category": "针织连衣裙", "brand": "Uniqlo", "price": 259, "color": "米白", "size": "M", "seasons": ["秋", "冬"], "style": "正式", "tags": ["保暖"]},
        {"title": "A字连衣裙", "category": "A字裙", "brand": "GU", "price": 199, "color": "浅粉", "size": "S", "seasons": ["春", "夏"], "style": "休闲", "tags": ["透气"]},
        {"title": "吊带连衣裙", "category": "吊带裙", "brand": "H&M", "price": 179, "color": "黑色", "size": "M", "seasons": ["夏"], "style": "正式", "tags": ["透气"]},
    ]

    for it in items:
        if it["brand"] not in brand_names:
            it["brand"] = choice(list(brand_names))

    for it in items:
        cat = it["category"]
        if cat not in category_ids:
            raise RuntimeError(f"缺少分类：{cat}")
    return items


def seed_demo_wardrobe(db_path: Optional[str], count: int, clear_seed: bool) -> Tuple[int, int]:
    db = WardrobeDatabase(db_path=db_path) if db_path else WardrobeDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        if clear_seed:
            _clear_seed_data(cursor)

        top_parent_id = _ensure_category(cursor, None, "上衣", 1)
        bottom_parent_id = _ensure_category(cursor, None, "下装", 1)
        dress_parent_id = _ensure_category(cursor, None, "连衣裙", 1)
        coat_parent_id = _ensure_category(cursor, None, "外套", 1)

        category_map: Dict[str, int] = {}
        for name in ["T恤", "衬衫", "针织衫", "卫衣", "背心"]:
            category_map[name] = _ensure_category(cursor, top_parent_id, name, 2)
        for name in ["牛仔裤", "休闲裤", "短裤", "短裙", "半身裙"]:
            category_map[name] = _ensure_category(cursor, bottom_parent_id, name, 2)
        for name in ["A字裙", "衬衫裙", "碎花裙", "针织连衣裙", "吊带裙"]:
            category_map[name] = _ensure_category(cursor, dress_parent_id, name, 2)
        for name in ["夹克", "风衣", "羽绒服", "西装外套", "卫衣外套"]:
            category_map[name] = _ensure_category(cursor, coat_parent_id, name, 2)

        brand_candidates = ["Uniqlo", "ZARA", "H&M", "Nike", "Adidas", "ANTA", "Li-Ning", "GU"]
        brand_ids = {name: _ensure_brand(cursor, name) for name in brand_candidates}

        cursor.execute("SELECT id, name FROM functional_tags")
        tag_name_to_id = {row["name"]: int(row["id"]) for row in cursor.fetchall()}

        items = _build_seed_items(category_map, list(brand_ids.keys()))
        items = items[: max(0, count)]

        inserted_products = 0
        inserted_skus = 0

        for it in items:
            platform_id = f"seed-{uuid4().hex[:12]}"
            cursor.execute(
                """
                INSERT OR IGNORE INTO products (platform, platform_id, brand_id, category_id, title, base_price, sync_status, style)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Seed", platform_id, brand_ids[it["brand"]], category_map[it["category"]], it["title"], float(it["price"]), "seed", it["style"]),
            )
            if cursor.rowcount == 0:
                continue

            product_id = int(cursor.lastrowid)
            inserted_products += 1

            tag_ids = [tag_name_to_id[t] for t in it.get("tags", []) if t in tag_name_to_id]

            cursor.execute(
                """
                INSERT INTO product_skus (product_id, sku_id, color_name, size_name, seasons, tag_ids, price, stock, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    product_id,
                    f"seed-sku-{uuid4().hex[:10]}",
                    it["color"],
                    it["size"],
                    json.dumps(it["seasons"], ensure_ascii=False),
                    json.dumps(tag_ids, ensure_ascii=False),
                    float(it["price"]),
                    randint(5, 50),
                ),
            )
            inserted_skus += 1

        conn.commit()
        return inserted_products, inserted_skus
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--clear-seed", action="store_true")
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    products, skus = seed_demo_wardrobe(args.db, args.count, args.clear_seed)
    print(f"✓ 已写入 Seed 测试衣物：products={products}, skus={skus}")


if __name__ == "__main__":
    main()
