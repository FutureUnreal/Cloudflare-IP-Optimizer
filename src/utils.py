import logging
from pathlib import Path
from datetime import datetime

def setup_logging(name):
    """设置日志"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 文件处理器
    fh = logging.FileHandler(
        log_dir / f'{name}_{datetime.now():%Y%m%d_%H%M%S}.log'
    )
    fh.setLevel(logging.INFO)
    
    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def parse_ip_range(ip_range):
    """解析IP范围"""
    parts = ip_range.split('.')
    prefix = '.'.join(parts[:2])
    return prefix

def is_valid_ip(ip):
    """验证IP地址是否有效"""
    try:
        parts = ip.split('.')
        return len(parts) == 4 and \
               all(0 <= int(part) <= 255 for part in parts)
    except:
        return False

def calculate_percentile(values, percentile):
    """计算百分位数"""
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[index]