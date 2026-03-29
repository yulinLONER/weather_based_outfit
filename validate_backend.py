import sys
import os
import time
import json
import sqlite3
from datetime import datetime

# 设置路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.weather_service import WeatherService
from core.recommender import OutfitRecommender
from db.manager import WardrobeDatabase

class SystemValidator:
    def __init__(self):
        self.weather_svc = WeatherService()
        self.db_manager = WardrobeDatabase()
        self.recommender = OutfitRecommender()
        self.results = {}

    def log_test(self, category, name, success, details="", data=None):
        if category not in self.results:
            self.results[category] = []
        self.results[category].append({
            "name": name,
            "success": success,
            "details": details,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"[{category}] {status}: {name} - {details}")

    def test_1_api_connectivity(self):
        print("\n--- 1. API 连通性与数据验证 ---")
        start_time = time.time()
        # 测试 浙江宁波
        data = self.weather_svc.get_weather("浙江", "宁波")
        duration = time.time() - start_time
        
        if data['success']:
            fields = ['temperature', 'humidity', 'weather', 'wind']
            missing = [f for f in fields if f not in data]
            if not missing:
                self.log_test("API", "连通性与字段完整性", True, f"响应时间: {duration:.2f}s", data)
            else:
                self.log_test("API", "字段缺失", False, f"缺少字段: {missing}")
        else:
            self.log_test("API", "请求失败", False, data.get('error', '未知错误'))

    def test_2_recommender_logic(self):
        print("\n--- 2. 推荐算法逻辑验证 ---")
        scenarios = [
            {"temp": 35, "weather": "晴朗", "desc": "高温晴朗 (夏)"},
            {"temp": -5, "weather": "小雪", "desc": "低温严寒 (冬)"},
            {"temp": 18, "weather": "多云", "desc": "温和多云 (春秋)"},
            {"temp": 25, "weather": "大雨", "desc": "高温多雨 (夏)"}
        ]
        
        for sc in scenarios:
            recs, info = self.recommender.get_recommendations(sc['temp'], sc['weather'])
            success = len(recs) > 0
            details = f"输入: {sc['desc']} -> 匹配到 {len(recs)} 种风格"
            self.log_test("RECOMMENDER", f"场景测试: {sc['desc']}", success, details, {"recs": recs, "info": info})

    def test_3_db_management(self):
        print("\n--- 3. 数据库管理与持久化验证 ---")
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # A. 测试插入
            test_item = ("测试上衣", 1, "休闲", 10, 30, "春,秋", "晴朗")
            cursor.execute('''
                INSERT INTO clothing_items (name, category_id, style, min_temp, max_temp, suitable_seasons, weather_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', test_item)
            conn.commit()
            
            # B. 测试查询
            cursor.execute("SELECT * FROM clothing_items WHERE name='测试上衣'")
            row = cursor.fetchone()
            if row:
                self.log_test("DB", "数据持久化 (插入与查询)", True, "成功保存并检索到测试衣物")
            else:
                self.log_test("DB", "数据查询失败", False, "未能检索到刚刚插入的数据")
                
            # C. 测试数据完整性 (外键检查等)
            cursor.execute("SELECT COUNT(*) FROM clothing_categories")
            cat_count = cursor.fetchone()[0]
            self.log_test("DB", "数据完整性 (类别表)", cat_count > 0, f"当前拥有 {cat_count} 个服装类别")

            # 清理测试数据
            cursor.execute("DELETE FROM clothing_items WHERE name='测试上衣'")
            conn.commit()
            
        except Exception as e:
            self.log_test("DB", "异常处理测试", False, str(e))
        finally:
            conn.close()

    def test_4_e2e_integration(self):
        print("\n--- 4. 端到端全流程模拟 ---")
        try:
            # 步骤 1: 获取天气 (模拟浙江宁波)
            weather = self.weather_svc.get_weather("浙江", "宁波")
            if not weather['success']: raise Exception("API 步骤失败")
            
            # 步骤 2: 传递给推荐引擎
            recs, info = self.recommender.get_recommendations(weather['temperature'], weather['weather'], "休闲")
            
            # 步骤 3: 验证结果链
            if len(recs) > 0 and info['temperature'] == weather['temperature']:
                self.log_test("E2E", "全流程数据链", True, "从 API 到推荐引擎的数据传递准确无误")
            else:
                self.log_test("E2E", "全流程数据链", False, "推荐结果为空或温度不匹配")
        except Exception as e:
            self.log_test("E2E", "流程中断", False, str(e))

    def run_all(self):
        print("🚀 开始系统后端全面验证...")
        self.test_1_api_connectivity()
        self.test_2_recommender_logic()
        self.test_3_db_management()
        self.test_4_e2e_integration()
        print("\n" + "="*50)
        print("🏁 验证完成。")
        return self.results

if __name__ == "__main__":
    validator = SystemValidator()
    validator.run_all()
