# Cloudflare Smart IP

[![Test and Update DNS](https://github.com/yourusername/cloudflare-smart-ip/actions/workflows/update-worker.yml/badge.svg)](https://github.com/yourusername/cloudflare-smart-ip/actions/workflows/update-worker.yml)

A tool for automatically testing and optimizing Cloudflare IPs. It tests network connection quality using ITDOG testing nodes, updates the optimal IP pool based on different ISPs and regions, and automatically deploys to Cloudflare Worker.

[English](#english) | [简体中文](./README_CN.md)

## ✨ Features

- 🚀 Automatic IP quality testing using ITDOG nodes
- 📊 Smart ISP and region analysis
- 🔄 Automatic Worker configuration updates
- 🌐 Multi-region and multi-ISP support
- ⚡ Optimized for Chinese networks
- 🔍 Detailed test logs

## 🛠️ Supported Regions

- EAST: Shanghai, Jiangsu, Zhejiang, Anhui, Fujian, Jiangxi, Shandong
- NORTH: Beijing, Tianjin, Hebei, Shanxi, Inner Mongolia
- SOUTH: Guangdong, Guangxi, Hainan
- CENTRAL: Henan, Hubei, Hunan
- SOUTHWEST: Chongqing, Sichuan, Guizhou, Yunnan, Tibet
- NORTHWEST: Shaanxi, Gansu, Qinghai, Ningxia, Xinjiang
- NORTHEAST: Liaoning, Jilin, Heilongjiang

## 🌟 Supported ISPs

- China Telecom (CHINA_TELECOM)
- China Unicom (CHINA_UNICOM)
- China Mobile (CHINA_MOBILE)

## 🚀 Quick Start

1. Fork this repository

2. Set up Secrets in your GitHub repository:
```
CF_ACCOUNT_ID: Your Cloudflare Account ID
CF_API_TOKEN: Your Cloudflare API Token
CF_WORKER_NAME: Your Worker Name
```

3. Modify configuration file (`config/settings.json`):
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

4. Enable Github Actions

## 📝 Local Testing

```bash
# Clone repository
git clone https://github.com/yourusername/cloudflare-smart-ip.git
cd cloudflare-smart-ip

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CF_ACCOUNT_ID="your-account-id"
export CF_API_TOKEN="your-api-token"
export CF_WORKER_NAME="your-worker-name"

# Run tests
python -m src.main
```

## 📊 Results

After each run, you can find:
- `results/ip_pools_latest.json`: Latest IP pool configuration
- `logs/`: Detailed test and update logs

## 🔍 How it Works

1. IP Testing:
   - Uses ITDOG testing nodes across China
   - Tests connection quality for each IP
   - Analyzes latency and packet loss

2. Region Detection:
   - Uses Cloudflare region codes
   - Maps provinces to regions
   - Supports coordinate-based fallback

3. ISP Detection:
   - ASN-based ISP detection
   - Supports major Chinese ISPs
   - Handles unknown ASNs gracefully

4. Worker Updates:
   - Automatic configuration generation
   - Smart IP pool selection
   - Automatic deployment

## 📈 Testing Nodes

Using ITDOG nodes covering:
- Multiple regions in China
- Major Chinese ISPs
- Various network conditions

## ⚙️ Configuration

### IP Ranges (`config/ip_ranges.json`):
```json
{
    "ip_ranges": [
        "1.1.1.0",
        "1.0.0.0",
        "104.16.0.0"
    ]
}
```

### Settings (`config/settings.json`):
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

## 📃 License

[MIT License](./LICENSE)