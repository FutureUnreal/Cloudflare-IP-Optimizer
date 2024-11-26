import json
import asyncio
import websockets
import hashlib
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List
import time
from urllib.parse import urlparse
import ipaddress
import random

class IPTester:
    def __init__(self, config: Dict):
        self.config = config
        self.setup_logging()
        self.session = requests.Session()
        
        # ITDOG节点ID映射 
        self.NODE_MAPPING = {
            'CHINA_TELECOM': {
                'EAST': ['1227', '1312'],     # 上海、江苏
                'SOUTH': ['1169', '1135'],    # 广东深圳、海南
                'NORTH': ['1310', '1132'],    # 北京、天津
                'CENTRAL': ['1214', '1311'],  # 湖北武汉、湖南长沙
                'SOUTHWEST': ['1138', '1304'], # 重庆、四川
                'NORTHWEST': ['1124', '1127'], # 新疆、甘肃
                'NORTHEAST': ['1168', '1129']  # 辽宁、吉林
            },
            'CHINA_UNICOM': {
                'EAST': ['1254', '1275'],     # 上海、江苏
                'SOUTH': ['1278', '1264'],    # 广东、海南
                'NORTH': ['1273', '1266'],    # 北京、天津
                'CENTRAL': ['1276', '1277'],  # 湖北、湖南
                'SOUTHWEST': ['1253', '1226'], # 重庆、四川
                'NORTHWEST': ['1260', '1256'], # 新疆、甘肃
                'NORTHEAST': ['1301', '1268']  # 辽宁、吉林
            },
            'CHINA_MOBILE': {
                'EAST': ['1249', '1237'],     # 上海、江苏
                'SOUTH': ['1290', '1294'],    # 广东、海南
                'NORTH': ['1250', '1295'],    # 北京、天津
                'CENTRAL': ['1287', '1242'],  # 湖北、湖南
                'SOUTHWEST': ['1245', '1283'], # 重庆、四川
                'NORTHWEST': ['1279', '1282'], # 新疆、甘肃
                'NORTHEAST': ['1293', '1292']  # 辽宁、吉林
            }
        }

        # ITDOG API配置
        self.API_URL = "https://api.itdog.cn/api/ping"

    def setup_logging(self):
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/ip_test_{datetime.now():%Y%m%d_%H%M%S}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging

    def _x(self, input_str: str, key: str) -> str:
        """ITDOG的解密函数"""
        output = ""
        key = key + "PTNo2n3Ev5"
        for i, char in enumerate(input_str):
            char_code = ord(char) ^ ord(key[i % len(key)])
            output += chr(char_code)
        return output

    def _set_ret(self, guard: str) -> str:
        """设置ITDOG的Cookie"""
        guard_prefix = guard[:8]
        guard_num = int(guard[12:]) if len(guard) > 12 else 0
        calc_num = guard_num * 2 + 18 - 2
        encrypted = self._x(str(calc_num), guard_prefix)
        return base64.b64encode(encrypted.encode()).decode()

    async def test_with_itdog(self, ip: str, node_id: str) -> Dict:
        """使用ITDOG API测试单个IP"""
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.itdog.cn',
            'referer': 'https://www.itdog.cn/ping/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # 第一次请求获取Cookie
        if 'guardret' not in self.session.cookies:
            self.session.post('https://www.itdog.cn/ping/', headers=headers)

        if 'guard' in self.session.cookies:
            self.session.cookies['guardret'] = self._set_ret(self.session.cookies['guard'])

        # 发送ping测试请求
        response = self.session.post('https://www.itdog.cn/ping/', headers=headers)

        # 提取websocket信息
        pattern = re.compile(r"""var wss_url='(.*)';""")
        wss_url = pattern.search(response.text).group(1)
        pattern = re.compile(r"""var task_id='(.*)';""")
        task_id = pattern.search(response.text).group(1)

        # 生成task_token
        task_token = hashlib.md5(
            (task_id + "token_20230313000136kwyktxb0tgspm00yo5").encode()
        ).hexdigest()[8:-8]

        # 连接websocket获取结果
        async with websockets.connect(wss_url) as ws:
            await ws.send(json.dumps({
                "task_id": task_id,
                "task_token": task_token,
                "node_id": node_id,
                "ip": ip
            }))

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    
                    if data.get('type') == 'finished':
                        break
                        
                    if 'result' in data:
                        return {
                            'latency': float(data['result']),
                            'loss': float(data.get('loss', 0)),
                            'available': True
                        }
                except Exception:
                    break

        return {
            'latency': float('inf'),
            'loss': 100,
            'available': False
        }

    async def test_single_ip(self, ip: str) -> Dict:
        """测试单个IP在所有节点的连接质量"""
        results = {
            'ip': ip,
            'status': 'ok',
            'tests': {},
            'time': datetime.now().isoformat()
        }
        
        for isp, regions in self.NODE_MAPPING.items():
            if isp not in results['tests']:
                results['tests'][isp] = {}
                
            for region, node_ids in regions.items():
                best_result = {
                    'latency': float('inf'),
                    'loss': 100,
                    'available': False
                }
                
                # 测试该区域的所有节点
                for node_id in node_ids:
                    try:
                        result = await self.test_with_itdog(ip, node_id)
                        if result['available'] and result['latency'] < best_result['latency']:
                            best_result = result
                    except Exception as e:
                        self.logger.error(f"测试 {ip} 使用节点 {node_id} 失败: {str(e)}")
                        continue
                
                results['tests'][isp][region] = best_result
                
                # 短暂延迟避免请求过快
                await asyncio.sleep(1)

        return results

    def generate_ip_list(self) -> List[str]:
        """生成要测试的IP列表"""
        ip_list = []
        for ip_range in self.config['ip_ranges']:
            try:
                # 如果是CIDR格式
                network = ipaddress.ip_network(ip_range)
                segment_ips = list(map(str, network.hosts()))
            except ValueError:
                # 如果是简单的IP格式，解析前两段
                prefix = '.'.join(ip_range.split('.')[:2])
                segment_ips = [
                    f"{prefix}.{third}.{fourth}"
                    for third in range(256)
                    for fourth in range(1, 255)
                ]
            
            # 应用抽样率
            if 'sample_rate' in self.config:
                sample_size = int(len(segment_ips) * self.config['sample_rate'])
                segment_ips = random.sample(segment_ips, sample_size)
            
            ip_list.extend(segment_ips)
            
        return ip_list

    def chunk_ip_list(self, ip_list: List[str], chunk_size: int = 10) -> List[List[str]]:
        """将IP列表分成小批次"""
        for i in range(0, len(ip_list), chunk_size):
            yield ip_list[i:i + chunk_size]

    async def run_tests(self) -> Dict:
        """运行完整的测试流程"""
        # 生成IP列表
        ip_list = self.generate_ip_list()
        self.logger.info(f"共生成 {len(ip_list)} 个待测试IP")
        
        results = []
        for i, batch in enumerate(self.chunk_ip_list(ip_list)):
            self.logger.info(f"测试第 {i+1} 批IP...")
            
            # 使用asyncio并发测试
            tasks = [self.test_single_ip(ip) for ip in batch]
            batch_results = await asyncio.gather(*tasks)
            
            for result in batch_results:
                if result['status'] == 'ok':
                    results.append(result)
            
            # 每批次后等待一下，避免请求过快
            await asyncio.sleep(2)
        
        # 保存结果
        self.save_results(results)
        
        return results

    def save_results(self, results: List[Dict]):
        """保存测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        
        # 保存详细结果
        with open(results_dir / f'test_results_{timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # 保存最新结果的副本
        with open(results_dir / 'test_results_latest.json', 'w') as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"测试结果已保存")

    def start(self):
        """启动测试"""
        asyncio.run(self.run_tests())