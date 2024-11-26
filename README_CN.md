# Cloudflare Smart IP

[![Test and Update DNS](https://github.com/yourusername/cloudflare-smart-ip/actions/workflows/update-worker.yml/badge.svg)](https://github.com/yourusername/cloudflare-smart-ip/actions/workflows/update-worker.yml)

自动测试和优化 Cloudflare IP 的工具。使用 ITDOG 测速节点进行网络质量测试，根据不同运营商和地区自动更新最优 IP 池，并自动部署到 Cloudflare Worker。

[English](./README.md) | [简体中文](#简体中文)

## ✨ 特性

- 🚀 使用 ITDOG 节点自动测试 IP 质量
- 📊 智能分析运营商和地区
- 🔄 自动更新 Worker 配置
- 🌐 多区域、多运营商支持
- ⚡ 针对中国网络优化
- 🔍 详细的测试日志

## 🛠️ 支持的地区

- 华东 (EAST)：上海、江苏、浙江、安徽、福建、江西、山东
- 华北 (NORTH)：北京、天津、河北、山西、内蒙古
- 华南 (SOUTH)：广东、广西、海南
- 华中 (CENTRAL)：河南、湖北、湖南
- 西南 (SOUTHWEST)：重庆、四川、贵州、云南、西藏
- 西北 (NORTHWEST)：陕西、甘肃、青海、宁夏、新疆
- 东北 (NORTHEAST)：辽宁、吉林、黑龙江

## 🌟 支持的运营商

- 中国电信 (CHINA_TELECOM)
- 中国联通 (CHINA_UNICOM)
- 中国移动 (CHINA_MOBILE)

## 🚀 快速开始

1. Fork 本仓库

2. 在 GitHub 仓库中设置 Secrets:
```
CF_ACCOUNT_ID: Cloudflare 账户 ID
CF_API_TOKEN: Cloudflare API 令牌
CF_WORKER_NAME: Worker 名称
```

3. 修改配置文件 (`config/settings.json`):
```json
{
    "test_count": 4,
    "test_timeout": 2,
    "max_workers": 5,
    "ips_per_region": 2,
    "chunk_size": 10,
    "retry_times": 3
}
```

4. 启用 Github Actions

## 📝 本地测试

```bash
# 克隆仓库
git clone https://github.com/yourusername/cloudflare-smart-ip.git
cd cloudflare-smart-ip

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export CF_ACCOUNT_ID="你的账户ID"
export CF_API_TOKEN="你的API令牌"
export CF_WORKER_NAME="你的Worker名称"

# 运行测试
python -m src.main
```

## 📊 测试结果

每次运行后可以查看：
- `results/ip_pools_latest.json`: 最新的 IP 池配置
- `logs/`: 详细的测试和更新日志

## 🔍 工作原理

1. IP 测试：
   - 使用遍布全国的 ITDOG 测速节点
   - 测试每个 IP 的连接质量
   - 分析延迟和丢包率

2. 地区检测：
   - 使用 Cloudflare 地区代码
   - 省份到区域的映射
   - 支持坐标定位兜底

3. 运营商检测：
   - 基于 ASN 的运营商识别
   - 支持主要中国运营商
   - 优雅处理未知 ASN

4. Worker 更新：
   - 自动生成配置
   - 智能 IP 池选择
   - 自动部署

## 📈 测试节点

使用 ITDOG 节点覆盖：
- 中国多个地区
- 主要运营商
- 多种网络环境

## ⚙️ 配置说明

### IP 范围 (`config/ip_ranges.json`):
```json
{
    "ip_ranges": [
        "1.1.1.0",
        "1.0.0.0",
        "104.16.0.0"
    ]
}
```

### 设置 (`config/settings.json`):
```json
{
    "test_count": 4,
    "test_timeout": 2,
    "max_workers": 5,
    "ips_per_region": 2,
    "chunk_size": 10,
    "retry_times": 3
}
```

## 📃 许可证

[MIT 许可证](./LICENSE)