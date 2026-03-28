import sqlite3
import os
import json

class WardrobeDatabase:
    """商品数据模型系统数据库管理类 (已根据最新需求升级)"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'data', 'wardrobe.db')
        self.db_path = db_path
        
        # 始终确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 初始化数据库架构
        self.init_database()
            
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # 使结果可以通过列名访问
        return conn

    def init_database(self):
        """初始化商品标准化数据库架构 (核心功能模块)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. 品牌库 (需求: 包含主流服装品牌)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                logo_url TEXT,
                description TEXT,
                is_preset INTEGER DEFAULT 0
            )
        ''')
        
        # 2. 层级分类表 (需求: 一级、二级分类层级结构)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT NOT NULL,
                level INTEGER NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES categories(id)
            )
        ''')
        
        # 3. 材质枚举表 (需求: 棉、麻、丝等动态扩展)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # 4. 功能标签表 (需求: 保暖、防晒、速干等)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS functional_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # 5. 商品主表 (需求: 统一数据标准化，对接 TB/PDD/JD)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,         -- TB, PDD, JD
                platform_id TEXT NOT NULL,      -- 平台商品 ID
                brand_id INTEGER,
                category_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                main_image TEXT,
                base_price REAL,                -- 基础价格
                currency TEXT DEFAULT 'CNY',
                style TEXT,                     -- 风格偏好：休闲、商务、运动、正式等
                sync_status TEXT DEFAULT 'pending',
                last_sync_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brand_id) REFERENCES brands(id),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                UNIQUE(platform, platform_id)
            )
        ''')
        
        # 尝试为已有的 products 表添加 style 字段 (向下兼容)
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN style TEXT DEFAULT '休闲'")
        except sqlite3.OperationalError:
            pass # 列已存在
        
        # 6. 商品规格 SKU 表 (需求: 颜色、尺码、材质、功能标签、库存)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_skus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                sku_id TEXT,                    -- 平台 SKU ID
                color_name TEXT,                -- 颜色名称
                color_hex TEXT,                 -- 十六进制色值
                color_pantone TEXT,             -- Pantone 编号
                size_name TEXT,                 -- XS, S, M, L... 或自定义
                size_params TEXT,               -- 自定义尺码具体参数 (JSON)
                material_composition TEXT,      -- 材质成分 (JSON, 如 {"棉": 0.8, "聚酯": 0.2})
                tag_ids TEXT,                   -- 功能标签 ID 列表 (JSON array)
                seasons TEXT,                   -- 季节属性 (JSON array: ["春", "夏"])
                price REAL,                     -- SKU 价格
                stock INTEGER DEFAULT 0,        -- 实时库存
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # 7. 同步日志与质量监控 (需求: 错误日志记录和报警)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                action TEXT,                    -- fetch, update, delete
                status TEXT,                    -- success, error
                message TEXT,
                data_quality_score REAL,        -- 数据完整性评分
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 8. 缓存表 (需求: 优化 API 调用性能)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                expires_at DATETIME NOT NULL
            )
        ''')

        # 9. AI 配置表 (管理后台可视化配置)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 10. 用户行为事件（用于推荐个性化）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                event_type TEXT NOT NULL,
                item_id INTEGER,
                meta_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 11. 衣橱图片（BLOB 存储，保证多端一致）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wardrobe_images (
                product_id INTEGER PRIMARY KEY,
                image_blob BLOB NOT NULL,
                mime_type TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')

        # 插入基础种子数据
        self._insert_advanced_seed_data(cursor)
        
        conn.commit()
        conn.close()

    def _insert_advanced_seed_data(self, cursor):
        """插入满足需求的标准化种子数据"""
        # 1. 材质预设
        materials = [('棉',), ('麻',), ('丝',), ('羊毛',), ('聚酯纤维',), ('氨纶',), ('锦纶',)]
        cursor.executemany('INSERT OR IGNORE INTO materials (name) VALUES (?)', materials)
        
        # 2. 功能标签预设
        tags = [('保暖',), ('防晒',), ('速干',), ('透气',), ('防水',), ('抗皱',)]
        cursor.executemany('INSERT OR IGNORE INTO functional_tags (name) VALUES (?)', tags)
        
        # 3. 层级分类预设
        # 一级分类
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            categories = [
                (None, '上衣', 1), (None, '下装', 1), (None, '连衣裙', 1), (None, '外套', 1)
            ]
            cursor.executemany('INSERT INTO categories (parent_id, name, level) VALUES (?, ?, ?)', categories)
            
            # 二级分类 (示例)
            top_id = cursor.execute("SELECT id FROM categories WHERE name='上衣'").fetchone()[0]
            bottom_id = cursor.execute("SELECT id FROM categories WHERE name='下装'").fetchone()[0]
            
            sub_categories = [
                (top_id, 'T恤', 2), (top_id, '衬衫', 2), (top_id, '针织衫', 2),
                (bottom_id, '牛仔裤', 2), (bottom_id, '休闲裤', 2), (bottom_id, '短裤', 2)
            ]
            cursor.executemany('INSERT INTO categories (parent_id, name, level) VALUES (?, ?, ?)', sub_categories)

        # 4. 品牌预设 (主流品牌)
        brands = [
            ('Uniqlo', '优衣库', 1), ('ZARA', '飒拉', 1), ('H&M', '海恩斯莫里斯', 1),
            ('Nike', '耐克', 1), ('Adidas', '阿迪达斯', 1), ('ANTA', '安踏', 1),
            ('Li-Ning', '李宁', 1), ('GU', '极优', 1)
        ]
        cursor.executemany('INSERT OR IGNORE INTO brands (name, description, is_preset) VALUES (?, ?, ?)', brands)

if __name__ == '__main__':
    db = WardrobeDatabase()
    print("✓ 高级商品管理系统数据库已初始化")
