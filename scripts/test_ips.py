import json
import subprocess
import socket
from concurrent.futures import ThreadPoolExecutor
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

    def generate_ip_list(self):
        """生成待测试的IP列表"""
        ip_list = []
        for base_ip in self.config['ip_ranges']:
            prefix = '.'.join(base_ip.split('.')[:-1])
            ip_list.extend(f"{prefix}.{i}" for i in range(1, 255))
        return ip_list

    def run_tests(self):
        """运行IP测试"""
        ip_list = self.generate_ip_list()
        self.logger.info(f"开始测试 {len(ip_list)} 个IP")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = [executor.submit(self.test_single_ip, ip) for ip in ip_list]
            for future in futures:
                try:
                    result = future.result()
                    if result['status'] == 'ok':
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"处理测试结果失败: {str(e)}")

        # 按延迟排序
        results.sort(key=lambda x: x['latency'])
        
        # 保存结果
        self.save_results(results)
        
        return results

    def save_results(self, results):
        """保存测试结果"""
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

if __name__ == "__main__":
    tester = IPTester()
    tester.run_tests()