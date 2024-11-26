import json
import logging
from pathlib import Path
from .ip_tester import IPTester
from .pool_updater import PoolUpdater
from .worker_updater import WorkerUpdater

def setup_logging(name='main'):
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)

def load_configs():
    """加载配置文件"""
    # 获取项目根目录路径
    root_dir = Path(__file__).parent.parent
    
    # 加载配置文件
    with open(root_dir / 'config' / 'settings.json') as f:
        settings = json.load(f)
    
    with open(root_dir / 'config' / 'ip_ranges.json') as f:
        ip_ranges = json.load(f)
    
    settings.update(ip_ranges)
    
    return settings

def main():
    # 设置日志
    logger = setup_logging()
    logger.info("开始更新流程")

    try:
        # 加载配置
        config = load_configs()
        
        # 创建结果目录
        Path('results').mkdir(exist_ok=True)

        # 1. 测试IP
        logger.info("开始IP测试...")
        tester = IPTester(config)
        tester.start()  # 这里会保存测试结果到results目录

        # 2. 更新IP池
        logger.info("更新IP池配置...")
        pool_updater = PoolUpdater(config)
        ip_pools = pool_updater.update()  # 从最新的测试结果更新IP池

        # 3. 更新Worker
        logger.info("更新Cloudflare Worker...")
        worker_updater = WorkerUpdater(config)
        success = worker_updater.update(ip_pools)

        if success:
            logger.info("所有更新完成")
        else:
            logger.error("Worker更新失败")

    except Exception as e:
        logger.error(f"更新过程发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()