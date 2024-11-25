# Cloudflare IP Optimizer
[![Test and Update DNS](https://github.com/FutureUnreal/Cloudflare-IP-Optimizer/actions/workflows/ip-test.yml/badge.svg)](https://github.com/FutureUnreal/Cloudflare-IP-Optimizer/actions/workflows/ip-test.yml)

A tool for automatically testing and optimizing Cloudflare IPs. It tests network connection quality of specified IP ranges, finds the optimal IP, and automatically updates Cloudflare DNS records.

English | [简体中文](./README_CN.md)

## ✨ Features

- 🚀 Automatic IP connection quality testing
- 🔄 Automatic DNS record updates to optimal IP
- ⏱️ Scheduled task support
- 📊 Detailed test logs and results
- 🔌 Complete port connectivity testing
- 🛡️ Built-in exception handling and retry mechanism

## 🌟 Advantages
- Uses Cloudflare DNS service IP ranges for optimization
- Based on official infrastructure, ensuring stable and reliable connections
- Remains effective despite Cloudflare routing changes
- One-time deployment, continuous stable operation

## 🚀 Quick Start

### 1. Fork Repository
Click the `Fork` button in the top-right corner to copy this repository to your account.

### 2. Configure GitHub Secrets
Add the following secrets to your forked repository:
- `CF_API_TOKEN`: Cloudflare API Token
- `CF_ZONE_ID`: Cloudflare Zone ID
- `DOMAIN_NAME`: Domain to update (e.g., fast.example.com)

### 3. Get Cloudflare Configuration

#### Get API Token:
1. Visit [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. Create new API Token
3. Ensure the following permissions:
   - Zone - DNS - Edit
   - Zone - Zone - Read

#### Get Zone ID:
1. Log into Cloudflare Dashboard
2. Select your domain
3. Find Zone ID in the overview page

### 4. Customize Configuration
Modify `config.json`:
```json
{
  "ip_ranges": [
    "1.1.1.0",
    "1.0.0.0"
  ],
  "test_count": 4,        // number of ping tests
  "test_timeout": 2,      // timeout in seconds
  "max_workers": 20,      // concurrent test workers
  "best_ip_count": 10,     // number of best IPs to keep
  "chunk_size": 1000      // number of IPs tested per batch
}
```

### 5. Enable GitHub Actions
1. Go to the Actions page in your repository
2. Click to enable Actions
3. You can manually trigger a workflow test run

## 📊 How It Works
1. Triggered by schedule or manually
2. Concurrent testing of specified IP ranges
3. Sorting and filtering based on latency and connectivity
4. Automatic Cloudflare DNS record updates
5. Saving test results and logs

## 🔍 Test Results
After each run, you can view in the Actions page:
- Complete test logs
- List of optimal IPs
- DNS update status
- Test statistics

## 💻 Local Testing
To run tests locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Test IPs
python scripts/test_ips.py

# Update DNS (environment variables required)
python scripts/update_dns.py
```

## ⚠️ Notes
1. Set reasonable test frequency, recommended interval no less than 1 hour
2. Regularly check GitHub Actions logs
3. Ensure correct Cloudflare API Token permissions
4. Check Actions logs first if issues occur

## 🤝 Contributing
Welcome to submit Issues and Pull Requests to make this tool better!

## 📝 License
[MIT License](./LICENSE)
