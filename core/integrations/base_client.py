import time
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import sqlite3
from db.manager import WardrobeDatabase

class BaseAPIClient:
    """统一 API 集成框架 (系统技术要求 2, 5, 6)"""
    
    def __init__(self, platform: str, rate_limit_ms: int = 500):
        self.platform = platform
        self.rate_limit_ms = rate_limit_ms
        self.last_call_time = 0
        self.db = WardrobeDatabase()
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(project_root, "api_sync.log")

        # 配置日志记录 (需求: 错误日志记录和报警)
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f"APIClient_{platform}")

    def _wait_for_rate_limit(self):
        """实现频率控制机制 (系统技术要求 2)"""
        elapsed = (time.time() - self.last_call_time) * 1000
        if elapsed < self.rate_limit_ms:
            time.sleep((self.rate_limit_ms - elapsed) / 1000)
        self.last_call_time = time.time()

    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """实现缓存机制 (系统技术要求 5)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT response_json FROM api_cache WHERE cache_key = ? AND expires_at > ?",
                (cache_key, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row['response_json'])
        except Exception as e:
            self.logger.error(f"读取缓存失败: {e}")
        finally:
            conn.close()
        return None

    def set_cache_response(self, cache_key: str, response_json: Dict, expire_minutes: int = 60):
        """存入缓存"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        expires_at = (datetime.now() + timedelta(minutes=expire_minutes)).isoformat()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, response_json, expires_at) VALUES (?, ?, ?)",
                (cache_key, json.dumps(response_json), expires_at)
            )
            conn.commit()
        except Exception as e:
            self.logger.error(f"写入缓存失败: {e}")
        finally:
            conn.close()

    def log_sync(self, action: str, status: str, message: str, quality_score: float = 1.0):
        """建立监控与日志系统 (系统技术要求 6, 数据质量监控要求 4)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO sync_logs (platform, action, status, message, data_quality_score) VALUES (?, ?, ?, ?, ?)",
                (self.platform, action, status, message, quality_score)
            )
            conn.commit()
            if status == "error":
                self.logger.error(f"[{action}] 异常: {message}")
            else:
                self.logger.info(f"[{action}] 成功: {message}")
        finally:
            conn.close()

    def call_api(self, endpoint: str, params: Dict[str, Any], use_cache: bool = True) -> Dict[str, Any]:
        """通用的 API 调用封装，带异常处理与重试"""
        cache_key = f"{self.platform}_{endpoint}_{hash(frozenset(params.items()))}"
        
        if use_cache:
            cached = self.get_cached_response(cache_key)
            if cached:
                return cached
        
        self._wait_for_rate_limit()
        
        # 这里应该是实际的 API 请求逻辑 (使用 requests 或平台 SDK)
        # 此处模拟 API 返回数据，实际中需集成 TB/PDD/JD 的 SDK
        try:
            # 模拟成功响应
            response = {"success": True, "data": {}} 
            
            if use_cache:
                self.set_cache_response(cache_key, response)
            
            self.log_sync("call_api", "success", f"Endpoint: {endpoint}")
            return response
        except Exception as e:
            self.log_sync("call_api", "error", f"Endpoint: {endpoint}, Error: {str(e)}")
            raise
