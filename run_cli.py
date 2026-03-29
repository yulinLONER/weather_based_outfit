import os
import sys
from api.weather_service import WeatherService
from core.recommender import OutfitRecommender

def main():
    print("🌤️  智能穿搭推荐系统 (命令行版)")
    print("-" * 30)
    
    # 1. 初始化服务
    weather_svc = WeatherService()
    recommender = OutfitRecommender()
    
    # 2. 获取输入
    province = input("请输入省份 (默认: 北京): ").strip() or "北京"
    city = input("请输入城市 (默认: 北京): ").strip() or "北京"
    
    print(f"\n🔍 正在获取 {province} {city} 的天气...")
    weather_data = weather_svc.get_weather(province, city)
    
    if not weather_data['success']:
        print(f"❌ 错误: {weather_data['error']}")
        return
        
    temp = weather_data['temperature']
    weather = weather_data['weather']
    
    print(f"✅ 当前天气: {temp}℃ | {weather}")
    print(f"💧 湿度: {weather_data['humidity']}% | 🌬️ 风力: {weather_data['wind']}")
    
    print("\n👔 风格偏好: [1] 休闲  [2] 商务  [3] 运动  [4] 正式  [其他/回车] 全部")
    style_choice = input("请输入序号或名称\n（ [1] 休闲  [2] 商务  [3] 运动  [4] 正式  [其他/回车] 全部: ").strip()
    style_map = {"1": "休闲", "2": "商务", "3": "运动", "4": "正式"}
    style_preference = style_map.get(style_choice, style_choice if style_choice in style_map.values() else None)
    
    # 3. 生成推荐
    recommendations, info = recommender.get_recommendations(temp, weather, style_preference)
    
    # 4. 输出结果
    recommender.print_recommendations(recommendations, info)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 已退出程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
