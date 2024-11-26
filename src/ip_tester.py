import json
import asyncio
import websockets
import hashlib
import base64
import requests
import re
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
        
        # 设置基本的会话headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
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

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.DEBUG,  # 使用DEBUG级别来获取更详细的日志
            format='%(asctime)s - %(message)s'
        )
        self.logger = logging

    def generate_ip_list(self) -> List[str]:
        """
        生成要测试的IP列表
        - 1.1.0.0/16 网段
        - 1.0.0.0/16 网段
        """
        ip_list = []
        prefixes = ['1.1', '1.0']  # 前两段

        # 从ip_ranges.json加载配置
        with open('config/ip_ranges.json') as f:
            ip_config = json.load(f)
        
        skip_ips = set(ip_config.get('skip_ips', []))
        start_from = ip_config.get('start_from', {})
        
        for prefix in prefixes:
            # 遍历第三段
            for third in range(256):
                # 遍历第四段
                for fourth in range(256):
                    ip = f"{prefix}.{third}.{fourth}"
                    # 跳过特定IP
                    if ip in skip_ips:
                        continue
                    # 根据start_from配置跳过特定范围
                    if (f"{prefix}.{third}" in start_from and 
                        fourth < start_from[f"{prefix}.{third}"]):
                        continue
                    ip_list.append(ip)
        
        # 应用抽样率
        if 'sample_rate' in self.config:
            sample_size = int(len(ip_list) * self.config['sample_rate'])
            ip_list = random.sample(ip_list, sample_size)
        
        self.logger.info(f"生成IP列表: 总计 {len(ip_list)} 个IP")
        return ip_list

    def itdog_batch_ping(self, ip: str, node_id: str) -> Dict:
        """使用ITDOG批量测试接口"""
        try:
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://www.itdog.cn',
                'pragma': 'no-cache',
                'referer': 'https://www.itdog.cn/ping/',  # 修改这里
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 构建测试数据
            data = {
                'host': ip,
                'node_id': node_id,  # 修改这里
                'check_mode': 'fast'  # 添加这个参数
            }

            # 发送测试请求
            response = self.session.post(
                'https://www.itdog.cn/ping/',  # 修改URL
                headers=headers,
                data=data,
                timeout=10
            )

            # 添加调试日志
            self.logger.debug(f"Response for {ip} from node {node_id}: {response.text}")

            if response.status_code != 200:
                self.logger.error(f"请求失败: {response.status_code}")
                return self._get_failed_result()

            # 检查是否有频率限制提示
            if '检测频率过高' in response.text:
                self.logger.warning(f"节点 {node_id} 频率限制")
                time.sleep(self.config.get('retry_delay', 60))
                return self._get_failed_result()

            # 使用更灵活的正则表达式来匹配结果
            time_pattern = r'time=(\d+\.?\d*)\s*ms'
            loss_pattern = r'(\d+)%\s*packet\s*loss'

            times = re.findall(time_pattern, response.text)
            loss_match = re.search(loss_pattern, response.text)

            if times:
                # 计算平均延迟
                latencies = [float(t) for t in times]
                avg_latency = sum(latencies) / len(latencies)
                loss = float(loss_match.group(1)) if loss_match else 0

                self.logger.info(f"IP {ip} 通过节点 {node_id} 测试成功: 延迟={avg_latency}ms, 丢包={loss}%")

                return {
                    'latency': avg_latency,
                    'loss': loss,
                    'available': True
                }
            
            self.logger.warning(f"IP {ip} 通过节点 {node_id} 测试未返回延迟数据")
            return self._get_failed_result()

        except Exception as e:
            self.logger.error(f"测试 {ip} 使用节点 {node_id} 失败: {str(e)}")
            return self._get_failed_result()

    def _get_failed_result(self) -> Dict:
        """返回失败结果"""
        return {
            'latency': float('inf'),
            'loss': 100,
            'available': False
        }

    async def test_ip(self, ip: str) -> Dict:
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
                best_result = self._get_failed_result()
                
                # 测试该区域的所有节点
                for node_id in node_ids[:self.config['nodes_per_test']]:
                    try:
                        # 添加请求间隔
                        await asyncio.sleep(self.config.get('min_request_interval', 5))
                        
                        result = self.itdog_batch_ping(ip, node_id)
                        if result['available'] and result['latency'] < best_result['latency']:
                            best_result = result
                    except Exception as e:
                        self.logger.error(f"测试 {ip} 使用节点 {node_id} 失败: {str(e)}")
                        continue
                
                results['tests'][isp][region] = best_result

        return results

    def chunk_ip_list(self, ip_list: List[str]) -> List[List[str]]:
        """将IP列表分成小批次"""
        chunk_size = self.config.get('chunk_size', 2)
        for i in range(0, len(ip_list), chunk_size):
            yield ip_list[i:i + chunk_size]

    async def run_tests(self) -> Dict:
        """运行完整的测试流程"""
        ip_list = self.generate_ip_list()
        self.logger.info(f"开始测试 {len(ip_list)} 个IP")
        
        results = []
        total_batches = len(ip_list) // self.config['chunk_size'] + 1
        
        for i, batch in enumerate(self.chunk_ip_list(ip_list)):
            self.logger.info(f"测试第 {i+1}/{total_batches} 批 ({len(batch)} 个IP)")
            
            # 测试这一批IP
            batch_results = []
            for ip in batch:
                try:
                    result = await self.test_ip(ip)
                    if result['status'] == 'ok':
                        batch_results.append(result)
                except Exception as e:
                    self.logger.error(f"测试IP {ip} 失败: {str(e)}")
            
            results.extend(batch_results)
            
            # 保存中间结果
            if i % 10 == 0:  # 每10批保存一次
                self.save_results(results, is_intermediate=True)
            
            # 批次间等待
            await asyncio.sleep(5)  # 每批等待5秒
            
            # 每测试50批后等待更长时间
            if i % 50 == 49:
                self.logger.info("等待60秒后继续...")
                await asyncio.sleep(60)
        
        # 保存最终结果
        self.save_results(results)
        return results

    def save_results(self, results: List[Dict], is_intermediate: bool = False):
        """保存测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        
        # 保存结果
        filename = f'test_results_intermediate_{timestamp}.json' if is_intermediate else f'test_results_{timestamp}.json'
        with open(results_dir / filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        # 始终保存一份最新结果的副本
        with open(results_dir / 'test_results_latest.json', 'w') as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"已保存{' 中间' if is_intermediate else ''}测试结果: {len(results)} 个IP")

    def start(self):
        """启动测试"""
        asyncio.run(self.run_tests())