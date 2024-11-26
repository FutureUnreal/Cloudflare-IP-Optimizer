import re
import json
import base64
import hashlib
import asyncio
import requests
import websockets
import logging
from pathlib import Path
from datetime import datetime
import random
from typing import Dict, List

class IPTester:
    def __init__(self, config: Dict):
        self.config = config
        self.setup_logging()
        self.session = requests.Session()
        
        # 按运营商分组的节点ID
        self.NODE_IDS = {
            'TELECOM': '1227',  # 电信上海
            'UNICOM': '1254',   # 联通上海
            'MOBILE': '1249'    # 移动上海
        }

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('IPTester')

    def x(self, input_str: str, key: str) -> str:
        """用于生成guardret的辅助函数"""
        key = key + "PTNo2n3Ev5"
        output = ""
        for i, char in enumerate(input_str):
            char_code = ord(char) ^ ord(key[i % len(key)])
            output += chr(char_code)
        return output

    def set_ret(self, guard_cookie: str) -> str:
        """生成guardret cookie"""
        prefix = guard_cookie[:8]
        num = int(guard_cookie[12:]) if len(guard_cookie) > 12 else 0
        val = num * 2 + 18 - 2
        encrypted = self.x(str(val), prefix)
        return base64.b64encode(encrypted.encode()).decode()

    def generate_ip_list(self) -> List[str]:
        """
        生成要测试的IP列表
        只测试三个IP:
        - 1.1.1.2
        - 1.1.1.3
        - 1.0.0.2
        """
        ip_list = [
            '1.1.1.2'
        ]
        
        self.logger.info(f"生成IP列表: 总计 {len(ip_list)} 个IP")
        return ip_list

    async def get_data(self, ip: str, node_id: str) -> Dict:
        """获取单个IP的测试数据"""
        try:
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://www.itdog.cn',
                'referer': 'https://www.itdog.cn/batch_ping/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            data = {
                'host': ip,
                'node_id': node_id,
                'check_mode': 'fast'
            }

            # 先访问主页
            self.logger.info("访问主页...")
            self.session.get('https://www.itdog.cn/batch_ping/', headers=headers)
            await asyncio.sleep(1)

            # 首次POST请求获取guard cookie
            self.logger.info("发送POST请求...")
            response = self.session.post('https://www.itdog.cn/batch_ping/', headers=headers, data=data)
            
            if 'guard' in self.session.cookies:
                self.session.cookies['guardret'] = self.set_ret(self.session.cookies['guard'])

            # 发送测试请求
            response = self.session.post('https://www.itdog.cn/batch_ping/', headers=headers, data=data)
            content = response.text
            
            # 解析WebSocket信息
            wss_match = re.search(r"""var wss_url='(.*)';""", content)
            task_match = re.search(r"""var task_id='(.*)';""", content)
            
            if not wss_match or not task_match:
                raise ValueError("无法获取WebSocket信息")
                
            wss_url = wss_match.group(1)
            task_id = task_match.group(1)
            
            task_token = hashlib.md5(
                (task_id + "token_20230313000136kwyktxb0tgspm00yo5").encode()
            ).hexdigest()[8:-8]

            self.logger.info(f"连接到 WebSocket: {wss_url}")
            
            # WebSocket连接
            async with websockets.connect(wss_url) as websocket:
                await websocket.send(json.dumps({
                    "task_id": task_id,
                    "task_token": task_token
                }))

                while True:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                        data = json.loads(msg)
                        self.logger.debug(f"收到数据: {data}")
                        
                        # 成功收到ping结果
                        if 'result' in data:
                            try:
                                # 转换延迟为数字
                                latency = float(data['result'])
                                if latency > 0:
                                    self.logger.info(f"IP: {data['ip']} 延迟: {latency}ms")
                                    return {
                                        'latency': latency,
                                        'loss': 0,  # 成功返回意味着没有丢包
                                        'available': True
                                    }
                            except (ValueError, TypeError):
                                pass

                        # 检查是否结束
                        if data.get('type') == 'finished':
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning("WebSocket响应超时")
                        break
                    except Exception as e:
                        self.logger.error(f"处理WebSocket消息时出错: {str(e)}")
                        break

        except Exception as e:
            self.logger.error(f"测试过程发生错误: {str(e)}")
            
        return {
            'latency': float('inf'),
            'loss': 100,
            'available': False
        }

    async def test_ip(self, ip: str) -> Dict:
        """测试单个IP"""
        result = {
            'ip': ip,
            'status': 'ok',
            'tests': {}
        }

        for isp, node_id in self.NODE_IDS.items():
            try:
                await asyncio.sleep(2)  # 避免请求过快
                test_result = await self.get_data(ip, node_id)
                result['tests'][isp] = test_result
            except Exception as e:
                self.logger.error(f"测试 {ip} 使用节点 {node_id} 失败: {str(e)}")
                result['tests'][isp] = {
                    'latency': float('inf'),
                    'loss': 100,
                    'available': False
                }

        return result

    async def run_tests(self) -> List[Dict]:
        """运行测试"""
        ip_list = self.generate_ip_list()
        results = []
        
        for i, ip in enumerate(ip_list):
            self.logger.info(f"测试 IP {i+1}/{len(ip_list)}: {ip}")
            try:
                result = await self.test_ip(ip)
                results.append(result)
                
                # 每测试10个IP保存一次结果
                if (i + 1) % 10 == 0:
                    self.save_results(results, is_intermediate=True)
                    await asyncio.sleep(5)  # 多等待一会
                else:
                    await asyncio.sleep(2)  # 正常等待
                    
            except Exception as e:
                self.logger.error(f"测试IP {ip}失败: {str(e)}")

        self.save_results(results)
        return results

    def save_results(self, results: List[Dict], is_intermediate: bool = False):
        """保存结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        
        filename = f'test_results_intermediate_{timestamp}.json' if is_intermediate else f'test_results_{timestamp}.json'
        with open(results_dir / filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        with open(results_dir / 'test_results_latest.json', 'w') as f:
            json.dump(results, f, indent=2)

    def start(self):
        """启动测试"""
        asyncio.run(self.run_tests())