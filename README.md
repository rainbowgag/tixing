# 跨境直播线路客户管理系统 V1.0

私有化部署的 Flask + SQLite 后台管理系统，用于客户、设备、线路、远程管理信息、续费提醒、邮件通知、Excel 导出和数据库备份。

## 默认功能

- 管理员登录、Session 保护、修改密码、密码哈希存储
- 仪表盘：客户数、设备数、7 天内到期、3 天内到期、已到期、最近更新
- 客户、设备、线路、远程管理信息、续费记录 CRUD 和搜索
- 远程密码默认隐藏，点击按钮显示
- 全局搜索客户名称、设备名称、线路编号、远程地址和备注
- Excel 导出客户、设备、线路、续费记录
- 手动备份、下载备份、每日自动备份保留 30 天
- 每天 08:00 执行续费邮件提醒
- Bootstrap 响应式后台界面，支持深色模式

## 一键安装

把项目上传到 GitHub 后，在 Ubuntu 22.04 VPS 执行：

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USER/YOUR_REPO/main/deploy/install.sh | sudo bash -s -- \
  --repo https://github.com/YOUR_GITHUB_USER/YOUR_REPO.git \
  --domain t.yaml.uk \
  --email your-email@example.com \
  --admin-user admin \
  --admin-password '请改成强密码'
```

安装完成后访问 `https://t.yaml.uk`。

## Cloudflare DNS

在 Cloudflare 为 `yaml.uk` 添加 DNS 记录：

- 类型：`A`
- 名称：`t`
- 内容：`38.58.59.103`
- 代理状态：建议先设为 `DNS only`，证书申请成功后再按需开启代理

也可以使用 Cloudflare API：

```bash
export CF_API_TOKEN='你的 Cloudflare API Token'
export CF_ZONE_ID='yaml.uk 的 Zone ID'
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"type":"A","name":"t.yaml.uk","content":"38.58.59.103","ttl":1,"proxied":false}'
```

证书由 VPS 上的安装脚本通过 Certbot 自动申请。

## 本地运行

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
flask --app wsgi:app run
```

