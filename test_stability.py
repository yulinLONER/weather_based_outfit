#!/usr/bin/env python3
"""
项目稳定性测试脚本
测试所有核心模块是否能正常运行
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_stability():
    """运行稳定性测试"""
    print("🧪 开始项目稳定性测试...\n")
    
    results = []
    
    # 1. 测试数据库模块
    try:
        from db.manager import WardrobeDatabase
        db = WardrobeDatabase()
        results.append(("数据库模块", True, "OK"))
    except Exception as e:
        results.append(("数据库模块", False, str(e)))
    
    # 2. 测试推荐引擎
    try:
        from core.recommender import OutfitRecommender
        recommender = OutfitRecommender()
        season = recommender.get_season_from_date()
        results.append(("推荐引擎", True, f"OK (当前季节: {season})"))
    except Exception as e:
        results.append(("推荐引擎", False, str(e)))
    
    # 3. 测试天气服务
    try:
        from api.weather_service import WeatherService
        weather = WeatherService()
        results.append(("天气服务", True, "OK"))
    except Exception as e:
        results.append(("天气服务", False, str(e)))
    
    # 4. 测试数据模型
    try:
        from models.product import ProductSKU, Product
        sku = ProductSKU(
            sku_id="test",
            color_name="黑色",
            color_hex="#000000",
            seasons=["春", "秋"]
        )
        sku.validate()
        results.append(("数据模型", True, "OK"))
    except Exception as e:
        results.append(("数据模型", False, str(e)))
    
    # 5. 测试配置系统
    try:
        from config import get_config, get_config_dict
        cfg = get_config()
        cfg_dict = get_config_dict()
        results.append(("配置系统", True, f"OK (环境: {cfg_dict['FLASK_ENV']})"))
    except Exception as e:
        results.append(("配置系统", False, str(e)))
    
    # 6. 测试 AI 客户端
    try:
        from core.ai_client import is_ai_enabled
        ai_enabled = is_ai_enabled()
        status = "已启用" if ai_enabled else "未配置"
        results.append(("AI 客户端", True, f"OK ({status})"))
    except Exception as e:
        results.append(("AI 客户端", False, str(e)))
    
    # 7. 测试 AI 工具模块
    try:
        from api.ai_tools import AISettingsStore
        ai_store = AISettingsStore()
        results.append(("AI 工具", True, "OK"))
    except Exception as e:
        results.append(("AI 工具", False, str(e)))
    
    # 8. 测试 Flask 应用
    try:
        from web.app_web import app
        assert app is not None
        results.append(("Flask 应用", True, "OK"))
    except Exception as e:
        results.append(("Flask 应用", False, str(e)))
    
    # 打印结果
    print("=" * 60)
    passed = 0
    failed = 0
    
    for module, success, message in results:
        if success:
            print(f"✅ {module:20} {message}")
            passed += 1
        else:
            print(f"❌ {module:20} {message}")
            failed += 1
    
    print("=" * 60)
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("✅ 所有测试通过！项目稳定性良好。")
        return True
    else:
        print(f"⚠️  有 {failed} 个模块测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = test_stability()
    sys.exit(0 if success else 1)
