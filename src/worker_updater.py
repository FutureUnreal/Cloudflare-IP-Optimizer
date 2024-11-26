import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils import setup_logging

class WorkerUpdater:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logging('worker_updater')
        
        # Cloudflare API配置
        self.account_id = os.getenv('CF_ACCOUNT_ID')
        self.api_token = os.getenv('CF_API_TOKEN')
        self.worker_name = os.getenv('CF_WORKER_NAME')
        
        if not all([self.account_id, self.api_token, self.worker_name]):
            raise ValueError("Missing required environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/javascript"
        }
        
        self.base_url = "https://api.cloudflare.com/client/v4"

    def load_template(self) -> str:
        """加载Worker模板"""
        try:
            with open('templates/worker_template.js', 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"加载Worker模板失败: {str(e)}")
            raise

    def generate_worker_script(self, ip_pools: Dict) -> str:
        """生成Worker脚本"""
        template = self.load_template()
        
        # 替换IP池配置
        script = template.replace(
            '{{IP_POOLS}}',
            json.dumps(ip_pools, indent=2)
        ).replace(
            '{{UPDATE_TIME}}',
            datetime.now().isoformat()
        )
        
        return script

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def update_worker(self, script_content: str) -> bool:
        """更新Worker代码"""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{self.worker_name}"
            
            # 发送更新请求
            response = requests.put(
                url,
                headers=self.headers,
                data=script_content
            )
            
            if response.status_code == 200:
                self.logger.info(f"Worker更新成功: {self.worker_name}")
                return True
            else:
                self.logger.error(f"Worker更新失败: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"更新Worker时发生错误: {str(e)}")
            raise

    def update(self, ip_pools: Dict = None) -> bool:
        """更新Worker"""
        try:
            # 如果没有提供IP池，尝试加载最新的IP池配置
            if ip_pools is None:
                try:
                    with open('results/ip_pools_latest.json', 'r') as f:
                        ip_pools = json.load(f)
                except Exception as e:
                    self.logger.error(f"加载IP池配置失败: {str(e)}")
                    return False

            # 生成Worker脚本
            script_content = self.generate_worker_script(ip_pools)
            
            # 更新Worker
            return self.update_worker(script_content)
            
        except Exception as e:
            self.logger.error(f"更新过程发生错误: {str(e)}")
            return False