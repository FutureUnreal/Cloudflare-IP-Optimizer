# Cloudflare IP Optimizer

[![Test and Update DNS](https://github.com/yourusername/cloudflare-ip-optimizer/actions/workflows/ip-test.yml/badge.svg)](https://github.com/yourusername/cloudflare-ip-optimizer/actions/workflows/ip-test.yml)

一个用于自动测试和优选 Cloudflare IP 的工具。通过测试指定 IP 段的网络连接质量，找出最优 IP 并自动更新到 Cloudflare DNS 记录。

[English](./README.md) | 简体中文

## ✨ 特性

- 🚀 自动测试 IP 连接质量
- 🔄 自动更新 DNS 记录到最优 IP
- ⏱️ 支持定时任务
- 📊 详细的测试日志和结果
- 🔌 完整的端口连通性测试
- 🛡️ 内置异常处理和重试机制

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角的 `Fork` 按钮复制本仓库到你的账号。

### 2. 配置 GitHub Secrets

在你 fork 的仓库中添加以下 Secrets:

- `CF_API_TOKEN`: Cloudflare API Token
- `CF_ZONE_ID`: Cloudflare Zone ID
- `DOMAIN_NAME`: 需要更新的域名 (例如: fast.example.com)

### 3. 获取 Cloudflare 配置

#### 获取 API Token:
1. 访问 [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. 创建新的 API Token
3. 确保包含以下权限:
   - Zone - DNS - Edit
   - Zone - Zone - Read

#### 获取 Zone ID:
1. 登录 Cloudflare 控制台
2. 选择你的域名
3. 在右侧概述页面找到 Zone ID

### 4. 自定义配置

修改 `config.json`:
```json
{
  "ip_ranges": [
    "2.1.1.0",
    "2.0.0.0"
  ],
  "test_count": 4,        // ping测试次数
  "test_timeout": 2,      // 超时时间(秒)
  "max_workers": 20,      // 并发测试数
  "best_ip_count": 10     // 保留最佳IP数量
}
```

### 5. 启用 GitHub Actions

1. 进入仓库的 Actions 页面
2. 点击启用 Actions
3. 可以手动触发一次工作流测试配置

## 📊 工作原理

1. 定时或手动触发测试
2. 并发测试指定 IP 段的连接质量
3. 基于延迟和连通性排序筛选
4. 自动更新 Cloudflare DNS 记录
5. 保存测试结果和日志

## 🔍 测试结果

每次运行后，你可以在 Actions 页面查看：

- 完整的测试日志
- 最优 IP 列表
- DNS 更新状态
- 测试统计数据

## 💻 本地测试

如果需要在本地运行测试：

```bash
# 安装依赖
pip install -r requirements.txt

# 测试IP
python scripts/test_ips.py

# 更新DNS(需要设置环境变量)
python scripts/update_dns.py
```

## ⚠️ 注意事项

1. 合理设置测试频率，建议间隔不少于 1 小时
2. 定期检查 GitHub Actions 运行日志
3. 确保 Cloudflare API Token 权限正确
4. 遇到问题请先查看 Actions 日志

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request，让这个工具变得更好！

## 📝 License

[MIT License](./LICENSE)