# 服装商品管理系统 - 数据库设计文档 (交付标准 1)

## 1. 核心表结构说明

### 1.1 品牌表 (brands)
| 字段名 | 类型 | 说明 | 约束 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 自增 ID | PRIMARY KEY |
| name | TEXT | 品牌名称 | UNIQUE, NOT NULL |
| logo_url | TEXT | 品牌 Logo 地址 | |
| description | TEXT | 品牌描述 | |
| is_preset | INTEGER | 是否预设品牌 | 0: 手动输入, 1: 预设库 |

### 1.2 层级分类表 (categories)
| 字段名 | 类型 | 说明 | 约束 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 自增 ID | PRIMARY KEY |
| parent_id | INTEGER | 父分类 ID | FOREIGN KEY |
| name | TEXT | 分类名称 | NOT NULL |
| level | INTEGER | 分类级别 | 1: 一级, 2: 二级 |

### 1.3 商品主表 (products)
| 字段名 | 类型 | 说明 | 约束 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 自增 ID | PRIMARY KEY |
| platform | TEXT | 来源平台 (TB, PDD, JD) | NOT NULL |
| platform_id | TEXT | 平台侧商品 ID | UNIQUE (with platform) |
| brand_id | INTEGER | 所属品牌 ID | FOREIGN KEY |
| category_id | INTEGER | 所属分类 ID | FOREIGN KEY |
| title | TEXT | 商品标题 | NOT NULL |
| description | TEXT | 商品详情描述 | |
| main_image | TEXT | 主图 URL | |
| base_price | REAL | 基础价格 | |
| sync_status | TEXT | 同步状态 | pending, success, error |
| last_sync_at | DATETIME | 最后同步时间 | |

### 1.4 商品 SKU 表 (product_skus)
| 字段名 | 类型 | 说明 | 约束 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 自增 ID | PRIMARY KEY |
| product_id | INTEGER | 所属商品 ID | FOREIGN KEY |
| color_hex | TEXT | 十六进制色值 | 格式: #RRGGBB |
| color_pantone | TEXT | Pantone 色号 | |
| size_name | TEXT | 尺码名称 | XS-6XL 或自定义 |
| material_composition | TEXT | 材质成分 | JSON (如 {"棉": 0.8}) |
| tag_ids | TEXT | 功能标签 ID 列表 | JSON Array |
| seasons | TEXT | 季节属性 | JSON Array |
| stock | INTEGER | 实时库存 | |

## 2. 索引设计
- `idx_products_platform_id`: 基于 (platform, platform_id) 的复合唯一索引，用于加速同步查找。
- `idx_skus_product_id`: 基于 product_id 的索引，用于快速查询商品下的所有 SKU。
- `idx_brands_name`: 基于品牌名称的唯一索引，用于快速匹配品牌。

## 3. 数据一致性策略
- 使用 SQLite 事务确保商品主表与 SKU 表在同步时的一致性。
- 通过外键约束确保分类、品牌数据的引用完整性。
