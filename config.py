"""
配置管理模块 - 集中管理所有项目配置
优先级：命令行参数 > 环境变量 > 配置文件 > 默认值
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # 加载 .env 文件中的环境变量
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")


class Config:
    """基础配置类"""
    
    # ========== Flask 配置 ==========
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    FLASK_DEBUG = FLASK_ENV == "development"
    FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    
    # 内置应用配置
    JSON_AS_ASCII = False  # 支持中文
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    # ========== 数据库配置 ==========
    BASE_DIR = Path(__file__).parent
    DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "wardrobe.db"))
    
    @classmethod
    def get_db_path(cls) -> str:
        """获取数据库完整路径"""
        return cls.DB_PATH
    
    # ========== API 配置 ==========
    # AI API
    AI_API_KEY = os.environ.get("AI_API_KEY")
    AI_API_BASE_URL = os.environ.get("AI_API_BASE_URL", "https://api.openai.com").rstrip("/")
    AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
    AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "30"))
    
    # 天气 API
    WEATHER_API_TIMEOUT = int(os.environ.get("WEATHER_API_TIMEOUT", "10"))
    
    # ========== 日志配置 ==========
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = BASE_DIR / "logs"
    
    @classmethod
    def setup_logging(cls):
        """设置日志系统"""
        import logging
        
        # 确保日志目录存在
        cls.LOG_DIR.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=cls.LOG_LEVEL,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_DIR / "app.log"),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger(__name__)
    
    # ========== 验证配置 ==========
    @classmethod
    def validate(cls) -> bool:
        """验证配置的完整性"""
        errors = []
        
        # 检查生产环境的必需配置
        if cls.FLASK_ENV == "production":
            if not cls.FLASK_SECRET_KEY:
                errors.append("❌ FLASK_SECRET_KEY must be set in production")
        
        # 检查可选 AI 配置的完整性
        if cls.AI_API_KEY:
            if not cls.AI_API_BASE_URL:
                errors.append("⚠️  AI_API_BASE_URL recommended when AI_API_KEY is set")
        
        if errors:
            print("\n⚠️  Configuration Issues:")
            for error in errors:
                print(f"  {error}")
            return cls.FLASK_ENV != "production"  # 生产环境下必须有效
        
        return True
    
    # ========== 开发环境配置 ==========
    @classmethod
    def get_dev_config(cls):
        """获取开发环境特定配置"""
        return {
            "DEBUG": True,
            "TESTING": False,
            "JSON_SORT_KEYS": False
        }
    
    @classmethod
    def get_prod_config(cls):
        """获取生产环境特定配置"""
        return {
            "DEBUG": False,
            "TESTING": False,
            "PRESERVE_CONTEXT_ON_EXCEPTION": True
        }


class DevelopmentConfig(Config):
    """开发环境配置"""
    FLASK_ENV = "development"
    FLASK_DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    FLASK_ENV = "production"
    FLASK_DEBUG = False
    
    @classmethod
    def validate(cls) -> bool:
        """生产环境必须验证所有关键配置"""
        if not cls.FLASK_SECRET_KEY:
            raise RuntimeError(
                "❌ ERROR: FLASK_SECRET_KEY must be set in production. "
                "Set it in your .env file or environment variables."
            )
        return super().validate()


class TestingConfig(Config):
    """测试环境配置"""
    FLASK_ENV = "testing"
    FLASK_DEBUG = True
    TESTING = True
    DB_PATH = str(Config.BASE_DIR / "data" / "test_wardrobe.db")


# 根据环境选择配置
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

def get_config() -> type:
    """获取当前环境的配置类"""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)


def get_config_dict() -> dict:
    """获取当前环境的配置字典"""
    config_class = get_config()
    result = {
        "FLASK_ENV": config_class.FLASK_ENV,
        "DEBUG": config_class.FLASK_DEBUG,
        "SECRET_KEY": config_class.FLASK_SECRET_KEY,
        "DB_PATH": config_class.DB_PATH,
        "AI_ENABLED": bool(config_class.AI_API_KEY),
    }
    return result


if __name__ == "__main__":
    # 便捷测试：python config.py
    config = get_config()
    print(f"🔧 Current Config: {config.__name__}")
    print(f"📝 FLASK_ENV: {config.FLASK_ENV}")
    print(f"🗄️  DB_PATH: {config.DB_PATH}")
    print(f"🤖 AI Enabled: {bool(config.AI_API_KEY)}")
    print(f"✅ Config Valid: {config.validate()}")
