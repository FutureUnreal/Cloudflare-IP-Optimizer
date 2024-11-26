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
        self.ip_pools = {
            isp: {region: [] for region in config['regions']}
            for isp in config['isps']
        }

        # ISP名称映射
        self.isp_mapping = {
            'TELECOM': 'CHINA_TELECOM',
            'UNICOM': 'CHINA_UNICOM',
            'MOBILE': 'CHINA_MOBILE'
        }

    def load_test_results(self) -> Dict:
        """加载最新的测试结果"""
        try:
            result_files = list(self.results_dir.glob('test_results_*.json'))
            if not result_files:
                raise FileNotFoundError("没有找到测试结果文件")
                
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
            self.logger.error("没有可用的测试结果")
            return self.ip_pools

        # 清空当前IP池
        for isp in self.ip_pools:
            for region in self.ip_pools[isp]:
                self.ip_pools[isp][region] = []

        # 处理每个IP的测试结果
        for result in results:
            if result['status'] != 'ok':
                continue

            ip = result['ip']
            for short_isp, test_data in result['tests'].items():
                # 转换ISP名称
                full_isp = self.isp_mapping.get(short_isp)
                if not full_isp:
                    self.logger.warning(f"未知的ISP类型: {short_isp}")
                    continue

                # 检查是否是有效的测试结果
                if (isinstance(test_data, dict) and
                    test_data.get('available') and
                    test_data.get('latency', float('inf')) < float('inf')):
                    
                    # 暂时都放入EAST区域
                    self.ip_pools[full_isp]['EAST'].append(ip)
                    self.logger.info(f"添加IP {ip} 到 {full_isp} EAST，延迟: {test_data['latency']}ms")

        # 保存结果
        self.save_results()
        return self.ip_pools

    def save_results(self):
        """保存IP池配置"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 确保结果目录存在
        self.results_dir.mkdir(exist_ok=True)
        
        # 保存当前配置
        with open(self.results_dir / f'ip_pools_{timestamp}.json', 'w') as f:
            json.dump(self.ip_pools, f, indent=2)
        
        # 保存最新配置的副本
        with open(self.results_dir / 'ip_pools_latest.json', 'w') as f:
            json.dump(self.ip_pools, f, indent=2)
            
        self.logger.info("IP池配置已保存")