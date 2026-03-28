import requests

class WeatherService:
    """天气服务，用于从 API 获取实时天气数据"""
    
    def __init__(self, api_id='10014438', api_key='5b2c37badf85574c4ba31f728e5229f5'):
        self.api_id = api_id
        self.api_key = api_key
        self.base_url = 'https://cn.apihz.cn/api/tianqi/tqyb.php'
        
    def get_weather(self, province, city):
        """获取指定省份和城市的天气"""
        params = {
            'id': self.api_id,
            'key': self.api_key,
            'sheng': province,
            'place': city
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if data.get('code') == 200:
                nowinfo = data.get('nowinfo', {})
                return {
                    'success': True,
                    'city': data.get('name', city),
                    'temperature': float(nowinfo.get('temperature', 20)),
                    'weather': data.get('weather1', '多云'),
                    'feels_like': nowinfo.get('feelst', 'N/A'),
                    'humidity': nowinfo.get('humidity', 'N/A'),
                    'wind': f"{nowinfo.get('windDirection', 'N/A')} {nowinfo.get('windScale', 'N/A')}级",
                    'uptime': nowinfo.get('uptime', 'N/A')
                }
            else:
                return {
                    'success': False,
                    'error': data.get('msg', '请求失败')
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
