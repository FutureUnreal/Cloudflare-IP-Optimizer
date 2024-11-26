import json
from pathlib import Path
from datetime import datetime
from typing import Dict
from .utils import setup_logging

class PoolUpdater:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logging('pool_updater')
        self.results_dir = Path('results')
        
        # 初始化IP池结构
        self.IP_POOLS = {
            isp: {region: [] for region in config['regions']}
            for isp in config['isps']
        }

    def load_test_results(self) -> Dict:
        """加载最新的测试结果"""
        try:
            # 获取最新的测试结果文件
            result_files = list(self.results_dir.glob('test_results_*.json'))
            if not result_files:
                raise FileNotFoundError("No test results found")
                
            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载测试结果失败: {str(e)}")
            return None

    def update(self) -> Dict:
        """更新IP池配置"""
        results = self.load_test_results()
        if not results:
            self.logger.error("没有找到可用的测试结果")
            return self.IP_POOLS

        # 清空现有IP池
        for isp in self.IP_POOLS:
            for region in self.IP_POOLS[isp]:
                self.IP_POOLS[isp][region] = []

        # 分析测试结果并更新IP池
        valid_ips = []
        for result in results:
            if result['status'] != 'ok':
                continue
                
            ip_data = {
                'ip': result['ip'],
                'tests': result['tests']
            }
            valid_ips.append(ip_data)

        # 为每个运营商和地区选择最佳IP
        for isp in self.IP_POOLS:
            for region in self.IP_POOLS[isp]:
                best_ips = self.select_best_ips(valid_ips, isp, region)
                self.IP_POOLS[isp][region] = best_ips

        # 保存更新后的IP池配置
        self.save_results()
        
        return self.IP_POOLS

    def select_best_ips(self, valid_ips: list, isp: str, region: str) -> list:
        """为指定运营商和地区选择最佳IP"""
        # 筛选该运营商和地区的所有测试结果
        region_results = []
        for ip_data in valid_ips:
            if (isp in ip_data['tests'] and 
                region in ip_data['tests'][isp] and 
                ip_data['tests'][isp][region]['available']):
                region_results.append({
                    'ip': ip_data['ip'],
                    'latency': ip_data['tests'][isp][region]['latency'],
                    'loss': ip_data['tests'][isp][region]['loss']
                })

        # 按延迟和丢包率排序
        region_results.sort(key=lambda x: (x['loss'], x['latency']))
        
        # 返回指定数量的最佳IP
        return [r['ip'] for r in region_results[:self.config['ips_per_region']]]

    def save_results(self):
        """保存IP池配置"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 确保结果目录存在
        self.results_dir.mkdir(exist_ok=True)
        
        # 保存完整配置
        with open(self.results_dir / f'ip_pools_{timestamp}.json', 'w') as f:
            json.dump(self.IP_POOLS, f, indent=2)
        
        # 保存最新配置的副本
        with open(self.results_dir / 'ip_pools_latest.json', 'w') as f:
            json.dump(self.IP_POOLS, f, indent=2)
            
        self.logger.info(f"IP池配置已保存")