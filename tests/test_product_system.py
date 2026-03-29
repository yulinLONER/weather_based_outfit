import unittest
from models.product import ProductSKU, Product, DataStandardizer
from db.manager import WardrobeDatabase
from core.services.sync_service import ProductSyncService
import os

class TestProductSystem(unittest.TestCase):
    """测试与验证要求 (需求: 单元测试验证模型约束、数据有效性、同步逻辑)"""
    
    def setUp(self):
        # 使用测试数据库
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_db_path = os.path.join(base_dir, "data", "test_wardrobe.db")
        self.db = WardrobeDatabase(self.test_db_path)
        self.sync_svc = ProductSyncService()
        self.sync_svc.db = self.db # 切换同步服务到测试库

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_sku_validation(self):
        """1. 单元测试: 验证 SKU 字段约束 (需求: 十六进制颜色、材质总和、季节验证)"""
        # A. 测试颜色校验
        sku = ProductSKU(sku_id="test_sku", color_name="红色", color_hex="INVALID")
        with self.assertRaises(ValueError):
            sku.validate()
            
        # B. 测试材质成分总和校验
        sku = ProductSKU(sku_id="test_sku", color_name="红色", material_composition={"棉": 0.8, "丝": 0.3})
        with self.assertRaises(ValueError):
            sku.validate()
            
        # C. 正确案例
        sku = ProductSKU(sku_id="test_sku", color_name="红色", color_hex="#FF0000", material_composition={"棉": 0.8, "丝": 0.2})
        sku.validate() # 不应抛出异常

    def test_data_mapping(self):
        """2. 单元测试: 验证不同平台数据的标准化映射 (系统技术要求 1)"""
        raw_tb = {"item_id": 12345, "title": "淘宝衬衫", "brand": "Uniqlo", "price": 100}
        product = DataStandardizer.map_platform_data("TB", raw_tb)
        self.assertEqual(product.platform, "TB")
        self.assertEqual(product.title, "淘宝衬衫")
        self.assertEqual(product.brand_name, "Uniqlo")

    def test_sync_to_db(self):
        """3. 集成测试: 验证全流程同步与持久化 (需求: 数据一致性测试)"""
        # 模拟同步一个商品
        success = self.sync_svc.sync_product("TB", "10001")
        self.assertTrue(success)
        
        # 验证数据库中是否存在
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE platform='TB' AND platform_id='10001'")
        product = cursor.fetchone()
        self.assertIsNotNone(product)
        self.assertEqual(product['title'], "淘宝精选：100%纯棉透气衬衫")
        
        # 验证 SKU 是否也同步了
        cursor.execute("SELECT count(*) as count FROM product_skus WHERE product_id=?", (product['id'],))
        sku_count = cursor.fetchone()['count']
        self.assertGreater(sku_count, 0)
        conn.close()

if __name__ == '__main__':
    unittest.main()
