import os
import sqlite3
from datetime import datetime

class OutfitRecommender:
    """穿搭推荐引擎 (核心逻辑)"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # 默认路径在 data/wardrobe.db
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'data', 'wardrobe.db')
        self.db_path = db_path
    
    def get_season_from_date(self, date_obj=None):
        """根据日期获取季节"""
        if date_obj is None:
            date_obj = datetime.now()
        
        month = date_obj.month
        
        if 3 <= month <= 5:
            return '春'
        elif 6 <= month <= 8:
            return '夏'
        elif 9 <= month <= 11:
            return '秋'
        else:
            return '冬'
    
    def get_weather_category(self, weather_desc):
        """将天气描述转换为类别"""
        weather_desc = weather_desc.lower()
        
        if any(word in weather_desc for word in ['晴', '晴朗', 'sunny']):
            return '晴朗'
        elif any(word in weather_desc for word in ['多云', 'cloudy']):
            return '多云'
        elif any(word in weather_desc for word in ['阴', 'overcast']):
            return '阴'
        elif any(word in weather_desc for word in ['雨', 'rain']):
            return '雨'
        else:
            return '多云'
    
    def get_recommendations(self, temperature, weather, style_preference=None, date_obj=None):
        """
        获取穿搭推荐 (核心推荐算法 - 升级版)
        
        Args:
            temperature: 温度（℃）
            weather: 天气描述
            style_preference: 风格偏好
            date_obj: 日期对象
        
        Returns:
            按风格分类的推荐列表
        """
        if date_obj is None:
            date_obj = datetime.now()
        
        temperature = float(temperature) if temperature else 20
        season = self.get_season_from_date(date_obj)
        weather_cat = self.get_weather_category(weather)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 升级版 SQL 查询：基于 products 和 product_skus
        query = '''
            SELECT DISTINCT 
                c.name as category,
                p.title,
                s.color_name,
                s.size_name,
                p.platform,
                s.price
            FROM products p
            JOIN product_skus s ON p.id = s.product_id
            JOIN categories c ON p.category_id = c.id
            WHERE s.seasons LIKE ? AND s.is_active = 1
        '''
        
        # 简单的温度过滤逻辑：如果数据库中没有显式的温度区间，可以根据季节逻辑
        # 在新模型中，我们主要根据 seasons 字段 (JSON array) 匹配
        params = [f'%{season}%']
        
        # 增加风格过滤条件
        if style_preference and style_preference != '\u5168\u90e8':
            query += ' AND p.style = ?'
            params.append(style_preference)
            
        # 这里先按分类聚合
        query += " ORDER BY c.name"
        
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        
        # 结果整理
        recommendations = {}
        for row in results:
            cat = row['category']
            item_desc = f"{row['title']} ({row['color_name']} - {row['size_name']})"
            
            if cat not in recommendations:
                recommendations[cat] = []
            recommendations[cat].append(item_desc)
        
        conn.close()
        
        # 为了兼容旧版 UI，将结果包装在 "默认" 风格下
        return {"推荐穿搭": recommendations}, {
            'temperature': temperature,
            'weather': weather,
            'season': season,
            'date': date_obj.strftime('%Y-%m-%d'),
            'style_preference': style_preference or '全部'
        }

    def print_recommendations(self, recommendations, weather_info):
        """格式化输出推荐信息 (用于 CLI)"""
        print(f"\n{'='*60}")
        print(f"👕 穿搭推荐 | {weather_info['date']} | {weather_info['temperature']}℃ {weather_info['weather']}")
        print(f"{'='*60}")
        
        if not recommendations:
            print("⚠️  未找到合适的穿搭，请检查数据库。")
            return
            
        for style, categories in recommendations.items():
            print(f"【{style}风格】")
            for cat, items in categories.items():
                print(f"  • {cat}: {' / '.join(items)}")
            print()
        print(f"{'='*60}\n")
