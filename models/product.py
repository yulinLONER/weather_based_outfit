from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
import re

@dataclass
class ProductSKU:
    """商品 SKU 数据模型 (需求: 材质、颜色、尺码、功能标签、季节)"""
    sku_id: str
    color_name: str
    color_hex: str = ""           # 格式: #FF0000
    color_pantone: str = ""       # 格式: Pantone 19-4052 TCX
    size_name: str = ""           # XS, S, M, L...
    size_params: Dict = field(default_factory=dict) # 自定义尺码参数
    material_composition: Dict[str, float] = field(default_factory=dict) # {"棉": 0.8}
    tag_ids: List[int] = field(default_factory=list)
    seasons: List[str] = field(default_factory=list) # ["春", "秋"]
    price: float = 0.0
    stock: int = 0
    is_active: bool = True

    def validate(self):
        """校验数据有效性 (测试与验证要求 1)"""
        if self.color_hex and not re.match(r'^#[0-9A-Fa-f]{6}$', self.color_hex):
            raise ValueError(f"无效的十六进制颜色格式: {self.color_hex}")
        
        valid_seasons = {"春", "夏", "秋", "冬"}
        for s in self.seasons:
            if s not in valid_seasons:
                raise ValueError(f"无效的季节属性: {s}")
        
        total_composition = sum(self.material_composition.values())
        if total_composition > 1.0001: # 允许微小浮点误差
            raise ValueError("材质成分总和不能超过 100%")

@dataclass
class Product:
    """商品主数据模型 (需求: 统一数据标准化)"""
    platform: str                # TB, PDD, JD
    platform_id: str
    title: str
    brand_name: str
    category_id: int
    description: str = ""
    main_image: str = ""
    base_price: float = 0.0
    skus: List[ProductSKU] = field(default_factory=list)
    
    def to_dict(self):
        """转换为字典以便存储或传输"""
        return {
            "platform": self.platform,
            "platform_id": self.platform_id,
            "title": self.title,
            "brand": self.brand_name,
            "category_id": self.category_id,
            "price": self.base_price,
            "sku_count": len(self.skus)
        }

class DataStandardizer:
    """数据标准化处理机制 (系统技术要求 1)"""
    
    @staticmethod
    def map_platform_data(platform: str, raw_data: Dict) -> Product:
        """将不同平台的原始数据映射到统一模型"""
        if platform == "TB":
            return DataStandardizer._map_taobao(raw_data)
        elif platform == "PDD":
            return DataStandardizer._map_pinduoduo(raw_data)
        elif platform == "JD":
            return DataStandardizer._map_jd(raw_data)
        else:
            raise ValueError(f"不支持的平台: {platform}")

    @staticmethod
    def _map_taobao(raw: Dict) -> Product:
        # 模拟淘宝数据映射逻辑
        return Product(
            platform="TB",
            platform_id=str(raw.get("item_id")),
            title=raw.get("title", ""),
            brand_name=raw.get("brand", "未知品牌"),
            category_id=raw.get("cid", 0),
            base_price=float(raw.get("price", 0))
        )

    @staticmethod
    def _map_pinduoduo(raw: Dict) -> Product:
        # 模拟拼多多数据映射逻辑
        return Product(
            platform="PDD",
            platform_id=str(raw.get("goods_id")),
            title=raw.get("goods_name", ""),
            brand_name=raw.get("brand_name", "未知品牌"),
            category_id=raw.get("cat_id", 0),
            base_price=float(raw.get("min_group_price", 0)) / 100 # 拼多多通常是分
        )

    @staticmethod
    def _map_jd(raw: Dict) -> Product:
        # 模拟京东数据映射逻辑
        return Product(
            platform="JD",
            platform_id=str(raw.get("skuId")),
            title=raw.get("skuName", ""),
            brand_name=raw.get("brandName", "未知品牌"),
            category_id=raw.get("cid", 0),
            base_price=float(raw.get("price", 0))
        )
