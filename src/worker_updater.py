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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def update_worker(self, ip_pools: Dict) -> bool:
        """更新Worker代码"""
        try:
            # 生成Worker代码
            script_content = self._generate_worker_script(ip_pools)
            
            # 添加这行来打印生成的脚本内容
            self.logger.debug(f"Generated script: {script_content}")
            
            # 验证脚本内容
            if not script_content.strip():
                self.logger.error("Worker脚本内容为空")
                return False

            # 构建请求URL
            url = f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{self.worker_name}"

            # 发送更新请求
            response = requests.put(
                url,
                headers=self.headers,
                data=script_content.encode('utf-8')
            )

            # 添加这行来打印响应内容
            self.logger.debug(f"Response content: {response.text}")

            if response.status_code == 200:
                self.logger.info(f"Worker更新成功: {self.worker_name}")
                self._save_worker_script(script_content)
                return True
            else:
                self.logger.error(f"Worker更新失败: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"更新Worker时发生错误: {str(e)}")
            raise

    def _generate_worker_script(self, ip_pools: Dict) -> str:
        """生成Worker脚本"""
        try:
            # 加载模板
            with open('templates/worker_template.js', 'r', encoding='utf-8') as f:
                template = f.read()

            # 替换变量
            script = template.replace(
                '{{IP_POOLS}}', 
                json.dumps(ip_pools, indent=2)
            ).replace(
                '{{UPDATE_TIME}}',
                datetime.now().isoformat()
            )

            return script

        except Exception as e:
            self.logger.error(f"生成Worker脚本失败: {str(e)}")
            raise

    def _save_worker_script(self, script_content: str):
        """保存Worker脚本副本"""
        try:
            results_dir = Path('results')
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 保存带时间戳的版本
            with open(results_dir / f'worker_{timestamp}.js', 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 保存最新版本
            with open(results_dir / 'worker_latest.js', 'w', encoding='utf-8') as f:
                f.write(script_content)

        except Exception as e:
            self.logger.error(f"保存Worker脚本失败: {str(e)}")

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

            # 更新Worker
            return self.update_worker(ip_pools)
            
        except Exception as e:
            self.logger.error(f"更新过程发生错误: {str(e)}")
            return False