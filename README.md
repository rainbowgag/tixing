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

## 多 VPS 主备备份

当前系统使用 SQLite，推荐一台主 VPS 写数据，其他 VPS 做备用机，不建议多台同时写。

备用 VPS 初始化，每台备用机执行一次：

```bash
curl -fsSL https://raw.githubusercontent.com/rainbowgag/tixing/main/deploy/setup-standby.sh | sudo bash -s -- \
  --domain t.yaml.uk \
  --port 25531 \
  --email 708805226@qq.com \
  --admin-user admin \
  --admin-password '请改成强密码'
```

主 VPS 安装同步任务，把 IP 换成三台备用 VPS 的 IP：

```bash
curl -fsSL https://raw.githubusercontent.com/rainbowgag/tixing/main/deploy/setup-primary-sync.sh | sudo bash -s -- \
  --replicas 'root@备用IP1,root@备用IP2,root@备用IP3' \
  --interval 30 \
  --keep 6
```

同步任务只同步 `/opt/line-crm/data/app.db` 和 `/opt/line-crm/.env`，不会同步虚拟环境、缓存、日志或历史大文件。主 VPS 本地只保留最近 6 个同步快照，备用 VPS 的邮件提醒和本地备份定时器默认关闭，避免重复发邮件和占用硬盘。

手动同步：

```bash
sudo /usr/local/sbin/linecrm-sync-replicas.sh
```

查看同步状态：

```bash
systemctl status linecrm-sync-replicas.timer --no-pager
journalctl -u linecrm-sync-replicas.service -n 80 --no-pager
```

主 VPS 挂了、备用 VPS 临时接管时，在接管的备用 VPS 上开启续费邮件提醒：

```bash
sudo systemctl enable --now line-crm-reminder.timer
```

说明：平时只让主 VPS 开启 `line-crm-reminder.timer`。备用 VPS 默认关闭这个定时器，避免多台服务器同时发送同一条续费提醒邮件。

## 本地运行

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
flask --app wsgi:app run
```
