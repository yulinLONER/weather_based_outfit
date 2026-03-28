from core.integrations.platform_clients import TaobaoClient, PinduoduoClient, JDClient
from db.manager import WardrobeDatabase
from typing import Dict, List, Optional
import json
from datetime import datetime

class ProductSyncService:
    """商品数据同步服务 (系统技术要求 3)"""
    
    def __init__(self):
        self.db = WardrobeDatabase()
        self.clients = {
            "TB": TaobaoClient(),
            "PDD": PinduoduoClient(),
            "JD": JDClient()
        }

    def sync_product(self, platform: str, platform_id: str) -> bool:
        """实时更新模式 (需求: 支持定时同步和实时更新两种模式)"""
        client = self.clients.get(platform)
        if not client:
            return False
            
        # 1. 获取详情 (API 集成)
        if platform == "TB":
            product = client.get_item_detail(platform_id)
        elif platform == "JD":
            product = client.get_sku_detail(platform_id)
        else:
            return False
            
        if not product:
            return False
            
        # 2. 映射到数据库 (数据标准化处理)
        return self._save_to_db(product)

    def _save_to_db(self, product) -> bool:
        """保存标准化商品数据到数据库"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            # A. 处理品牌 ID (若不存在则插入)
            cursor.execute("SELECT id FROM brands WHERE name = ?", (product.brand_name,))
            brand_row = cursor.fetchone()
            if brand_row:
                brand_id = brand_row['id']
            else:
                cursor.execute("INSERT INTO brands (name) VALUES (?)", (product.brand_name,))
                brand_id = cursor.lastrowid
            
            # B. 插入或更新商品主表 (需求: 统一数据模型架构)
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (platform, platform_id, brand_id, category_id, title, description, main_image, base_price, last_sync_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.platform, product.platform_id, brand_id, product.category_id,
                product.title, product.description, product.main_image, product.base_price,
                datetime.now().isoformat()
            ))
            db_product_id = cursor.lastrowid if cursor.lastrowid else 0 # 如果是 REPLACE，需要单独查询
            if not db_product_id:
                cursor.execute("SELECT id FROM products WHERE platform=? AND platform_id=?", (product.platform, product.platform_id))
                db_product_id = cursor.fetchone()['id']

            # C. 处理 SKU 信息 (需求: 颜色、尺码、材质、功能标签、库存)
            # 先逻辑删除旧 SKU
            cursor.execute("UPDATE product_skus SET is_active = 0 WHERE product_id = ?", (db_product_id,))
            
            for sku in product.skus:
                cursor.execute('''
                    INSERT INTO product_skus 
                    (product_id, sku_id, color_name, color_hex, color_pantone, size_name, 
                     size_params, material_composition, tag_ids, seasons, price, stock, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    db_product_id, sku.sku_id, sku.color_name, sku.color_hex, sku.color_pantone,
                    sku.size_name, json.dumps(sku.size_params), json.dumps(sku.material_composition),
                    json.dumps(sku.tag_ids), json.dumps(sku.seasons), sku.price, sku.stock
                ))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ 数据库保存失败: {e}")
            return False
        finally:
            conn.close()

    def run_scheduled_sync(self):
        """定时同步模式 (需求: 定期全量/增量同步)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT platform, platform_id FROM products WHERE sync_status != 'error'")
            products_to_sync = cursor.fetchall()
            
            print(f"⏰ 开始定时同步，共 {len(products_to_sync)} 个商品...")
            for p in products_to_sync:
                self.sync_product(p['platform'], p['platform_id'])
            print("🏁 定时同步任务完成。")
        finally:
            conn.close()
