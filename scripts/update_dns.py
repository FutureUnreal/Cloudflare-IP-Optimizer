import os
import json
import requests
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class CloudflareDNS:
    def __init__(self, token, zone_id):
        self.token = token
        self.zone_id = zone_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/dns_update_{datetime.now():%Y%m%d_%H%M%S}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def update_dns_record(self, domain: str, new_ip: str) -> bool:
        """更新DNS记录"""
        try:
            # 获取现有记录
            record_id = self._get_record_id(domain)
            
            if record_id:
                # 更新已存在的记录
                url = f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}"
                data = {
                    "type": "A",
                    "name": domain,
                    "content": new_ip,
                    "proxied": True
                }
                response = requests.put(url, headers=self.headers, json=data)
            else:
                # 创建新记录
                url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
                data = {
                    "type": "A",
                    "name": domain,
                    "content": new_ip,
                    "proxied": True
                }
                response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code in (200, 201):
                self.logger.info(f"已成功更新DNS记录: {domain} -> {new_ip}")
                return True
            else:
                self.logger.error(f"更新DNS记录失败: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"更新DNS记录时发生错误: {str(e)}")
            raise

    def _get_record_id(self, domain: str) -> str:
        """获取DNS记录ID"""
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        params = {"name": domain}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            records = response.json().get("result", [])
            if records:
                return records[0]["id"]
        return None

def main():
    # 获取环境变量
    token = os.getenv("CF_API_TOKEN")
    zone_id = os.getenv("CF_ZONE_ID")
    domain = os.getenv("DOMAIN_NAME")
    
    if not all([token, zone_id, domain]):
        logging.error("缺少必要的环境变量配置")
        return
    
    try:
        # 读取最佳IP
        with open('best_ips.json', 'r') as f:
            best_ips = json.load(f)
    except FileNotFoundError:
        logging.error("找不到best_ips.json文件")
        return
    
    if not best_ips:
        logging.error("没有可用的IP")
        return
    
    # 使用延迟最低的IP更新DNS
    best_ip = best_ips[0]["ip"]
    
    # 更新DNS记录
    cf = CloudflareDNS(token, zone_id)
    cf.update_dns_record(domain, best_ip)

if __name__ == "__main__":
    main()