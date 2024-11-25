import json
import subprocess
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging
import os
from pathlib import Path

class IPTester:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
        self.setup_logging()
        
    def load_config(self, config_path):
        with open(config_path) as f:
            config = json.load(f)
        return config
    
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

    def generate_ip_list(self):
        """生成要测试的IP列表 (/16网段)"""
        ip_list = []
        for base_ip in self.config['ip_ranges']:
            # 从基础IP中提取前两段
            prefix = '.'.join(base_ip.split('.')[:2])
            # 生成第三段和第四段的所有组合
            for third in range(256):
                for fourth in range(1, 255):
                    ip_list.append(f"{prefix}.{third}.{fourth}")
        return ip_list

    def test_single_ip(self, ip):
        """测试单个IP的连接质量"""
        try:
            cmd = ['ping', '-c', str(self.config['test_count']), 
                  '-W', str(self.config['test_timeout']), ip]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                avg_time = self.parse_ping_result(result.stdout)
                tcp_ok = self.test_tcp_ports(ip)
                return {
                    'ip': ip,
                    'status': 'ok',
                    'latency': avg_time,
                    'tcp_ok': tcp_ok,
                    'time': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"测试 {ip} 失败: {str(e)}")
        
        return {
            'ip': ip,
            'status': 'failed',
            'latency': float('inf'),
            'tcp_ok': False,
            'time': datetime.now().isoformat()
        }

    def parse_ping_result(self, output):
        """解析ping命令输出"""
        for line in output.split('\n'):
            if 'avg' in line:
                return float(line.split('/')[-3])
        return float('inf')

    def test_tcp_ports(self, ip, ports=[443, 80]):
        """测试TCP端口连通性"""
        for port in ports:
            try:
                with socket.create_connection((ip, port), timeout=2):
                    return True
            except:
                continue
        return False

    def chunk_ip_list(self, ip_list, chunk_size=1000):
        """将IP列表分块，避免一次测试太多IP"""
        for i in range(0, len(ip_list), chunk_size):
            yield ip_list[i:i + chunk_size]

    def save_intermediate_results(self, results):
        """保存中间结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'intermediate_results_{timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2)

    def save_results(self, results):
        """保存最终测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存完整结果
        with open(f'ip_test_results_{timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # 保存最佳IP列表
        best_ips = results[:self.config['best_ip_count']]
        with open('best_ips.json', 'w') as f:
            json.dump(best_ips, f, indent=2)
        
        self.logger.info(f"测试完成，找到 {len(results)} 个可用IP")
        if best_ips:
            self.logger.info(
                f"最佳IP: {best_ips[0]['ip']} "
                f"(延迟: {best_ips[0]['latency']}ms)"
            )

    def run_tests(self):
        """运行IP测试，分批处理"""
        all_ips = self.generate_ip_list()
        self.logger.info(f"总共生成 {len(all_ips)} 个IP地址")
        
        results = []
        chunk_size = self.config.get('chunk_size', 1000)
        for chunk_index, ip_chunk in enumerate(self.chunk_ip_list(all_ips, chunk_size)):
            self.logger.info(f"开始测试第 {chunk_index + 1} 批IP...")
            
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                chunk_futures = [executor.submit(self.test_single_ip, ip) for ip in ip_chunk]
                for future in as_completed(chunk_futures):
                    try:
                        result = future.result()
                        if result['status'] == 'ok':
                            results.append(result)
                    except Exception as e:
                        self.logger.error(f"处理测试结果时出错: {str(e)}")
            
            # 每批次结束后保存一次中间结果
            self.save_intermediate_results(results)
            
            # 输出当前进度
            self.logger.info(f"当前已测试 {len(results)} 个可用IP")
        
        # 按延迟排序
        results.sort(key=lambda x: x['latency'])
        
        # 保存最终结果
        self.save_results(results)
        
        return results

if __name__ == "__main__":
    tester = IPTester()
    tester.run_tests()