# NodeSeek RSS

NodeSeek RSS 是一个私人的 [NodeSeek](https://www.nodeseek.com/) RSS 监控程序。它会定时检查新帖子，匹配你配置的关键词，并通过 Telegram 和 Resend 邮件发送通知。

版本：`1.0.0`

本项目基于 [n-AChegYag/nodeseek-keywords](https://github.com/n-AChegYag/nodeseek-keywords) 开发。原项目提供了 Telegram 关键词监控基础能力，本项目在此基础上增加了 Resend 邮件通知、分通道通知状态、日志轮转、数据库保留清理和多架构 Docker 打包。

## 功能特性

- 关键词监控，支持大小写不敏感的普通子串匹配。
- 正则关键词匹配，并在添加时校验正则语法。
- 支持按 NodeSeek 版块过滤。
- 支持通过 Telegram 命令管理关键词。
- 支持 Telegram 和 Resend 邮件双通道通知。
- 记录每个通知通道的发送状态。
- 防洪机制：每轮超过上限时自动汇总通知。
- 首次启动静默，不推送历史旧帖子。
- 使用 SQLite 持久化数据，避免重复推送。
- RSS 健康告警。
- 可配置数据库清理策略。
- 可配置日志轮转和大小上限。
- 支持 Linux 直接运行和 Docker 部署。
- Docker 镜像支持 `linux/amd64` 和 `linux/arm64`。

## 支持的版块

| Slug | 版块 |
|---|---|
| `daily` | 日常 |
| `tech` | 技术 |
| `info` | 情报 |
| `review` | 测评 |
| `trade` | 交易 |
| `carpool` | 拼车 |
| `dev` | Dev |
| `photo-share` | 贴图 |
| `expose` | 曝光 |
| `sandbox` | 沙盒 |

## Docker 快速开始

```bash
docker run -d \
  --name nodeseek-rss \
  --restart unless-stopped \
  --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  lanxuewsr/nodeseek-rss:latest
```

也可以使用 Docker Compose：

```bash
cp .env.example .env
# 编辑 .env
docker compose up -d
```

查看运行状态：

```bash
docker ps --filter name=nodeseek-rss
docker logs -f nodeseek-rss
```

如果映射了 `./logs:/app/logs`，也可以直接查看宿主机上的日志文件：

```bash
tail -f ./logs/nodeseek-rss.log
```

## Linux 直接运行

推荐 Python 3.11+。

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env
python main.py
```

## 配置

| 变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `TELEGRAM_BOT_TOKEN` | 是 | - | BotFather 提供的 Telegram Bot Token |
| `ALLOWED_USER_ID` | 是 | - | 允许控制 Bot 的 Telegram 用户 ID |
| `RSS_BASE_URL` | 否 | `https://rss.nodeseek.com/` | NodeSeek RSS 地址 |
| `POLL_INTERVAL` | 否 | `60` | RSS 轮询间隔，单位秒 |
| `MAX_NOTIFICATIONS_PER_POLL` | 否 | `10` | 每轮最多单独发送的通知数量 |
| `RSS_FAIL_ALERT_THRESHOLD` | 否 | `3` | RSS 连续失败 N 次后发送健康告警 |
| `DATABASE_PATH` | 否 | `data/nodeseek-rss.db` | SQLite 数据库路径 |
| `SEEN_POSTS_RETENTION_DAYS` | 否 | `30` | 已读帖子去重记录保留天数 |
| `NOTIFICATIONS_RETENTION_DAYS` | 否 | `30` | 通知历史保留天数 |
| `CLEANUP_INTERVAL_HOURS` | 否 | `24` | 每 N 小时执行一次清理 |
| `LOG_DIR` | 否 | `logs` | 日志目录 |
| `LOG_FILE` | 否 | `nodeseek-rss.log` | 日志文件名 |
| `LOG_MAX_BYTES` | 否 | `104857600` | 单个活跃日志文件大小上限，默认 100 MB |
| `LOG_BACKUP_COUNT` | 否 | `1` | 日志轮转备份数量 |
| `EMAIL_ENABLED` | 否 | `true` | 是否启用 Resend 邮件通知 |
| `RESEND_API_KEY` | 邮件启用时必填 | - | Resend API Key |
| `RESEND_FROM` | 邮件启用时必填 | `NodeSeek Monitor <onboarding@resend.dev>` | 邮件发件人 |
| `RESEND_TO` | 邮件启用时必填 | - | 邮件收件人 |
| `RESEND_API_URL` | 否 | `https://api.resend.com/emails` | Resend API 地址 |
| `EMAIL_TIMEOUT_SECONDS` | 否 | `20` | 邮件请求超时时间 |

本项目不包含 SMTP2HTTP，邮件只通过 Resend 发送。

## 数据目录映射说明

Docker 容器内默认数据库路径是：

```text
data/nodeseek-rss.db
```

程序工作目录是 `/app`，因此容器内完整路径是：

```text
/app/data/nodeseek-rss.db
```

当你使用下面的映射时：

```bash
-v ./data:/app/data
```

数据库会保存到宿主机当前目录的：

```text
./data/nodeseek-rss.db
```

也就是说，`DATABASE_PATH=data/nodeseek-rss.db` 会被正确映射到宿主机目录。

## Telegram 命令

| 命令 | 说明 |
|---|---|
| `/start` `/help` | 查看帮助 |
| `/add <关键词> [--regex] [版块]` | 添加关键词 |
| `/remove <关键词>` | 删除关键词，会删除该关键词下所有版块配置 |
| `/pause <关键词>` | 暂停关键词 |
| `/resume <关键词>` | 恢复关键词 |
| `/list` | 查看关键词列表 |
| `/history [数量]` | 查看最近通知历史 |
| `/categories` | 查看可用版块 Slug |
| `/status` | 查看程序运行状态、邮件状态和清理配置 |

当前版本只能通过 Telegram 命令管理关键词；暂时没有 Web 管理界面，也没有通过环境变量预置关键词的功能。

## 关键词示例

```text
/add DMIT
/add 搬瓦工 trade
/add DMIT.*(CN2|GIA) --regex
/add (补货|回归|上新) --regex info
```

## 测试通知

当前版本没有单独的 `/test` 命令。

可用的基础测试方式：

1. 启动容器后查看日志，确认程序没有退出。
2. 在 Telegram 中向 Bot 发送 `/status`，如果收到回复，说明 Telegram 命令链路正常。
3. 配置一个容易命中的关键词，等待 NodeSeek RSS 出现新帖。

如需主动测试 Telegram + 邮件双通道，建议后续增加 `/test` 命令；当前版本暂未实现。

## Telegram Bot 使用说明

推荐为本程序新建一个专用 Telegram Bot。

技术上，只要你拥有 Bot Token，任意 Telegram Bot 都可以用于本程序，包括你之前接收 Komari 消息的 Bot。但需要注意：

- 一个 Bot Token 可以同时被多个程序调用 `sendMessage` 主动发消息。
- 但如果多个程序都要接收同一个 Bot 的用户命令或更新，容易互相影响。
- 本程序使用 long polling 接收 `/add`、`/status` 等命令；如果 Komari 或其他程序也在用同一个 Bot 接收更新，可能出现命令被其中一个程序消费、另一个程序收不到的情况。
- 如果只是 Komari 用这个 Bot 发送通知，而不接收命令，通常可以共用。
- 如果你希望稳定使用本程序的 Telegram 命令管理关键词，建议新建专用 Bot。

新建 Bot 步骤：

1. 在 Telegram 搜索 `@BotFather`。
2. 发送 `/newbot`。
3. 按提示输入 Bot 显示名称，例如 `NodeSeek RSS Monitor`。
4. 按提示输入 Bot 用户名，必须以 `bot` 结尾，例如 `nodeseek_rss_xxx_bot`。
5. BotFather 会返回一串 Token，把它填入 `.env` 的 `TELEGRAM_BOT_TOKEN`。
6. 获取你的 Telegram 用户 ID，可以搜索 `@userinfobot` 或 `@getmyid_bot`，把数字 ID 填入 `.env` 的 `ALLOWED_USER_ID`。
7. 启动程序后，打开新 Bot，发送 `/start`。
8. 发送 `/status` 验证程序是否正常响应。

## Docker 镜像

已发布标签：

```text
lanxuewsr/nodeseek-rss:1.0.0
lanxuewsr/nodeseek-rss:latest
```

手动构建多架构镜像：

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t lanxuewsr/nodeseek-rss:1.0.0 \
  -t lanxuewsr/nodeseek-rss:latest \
  --push .
```

## 数据保留和日志清理

清理任务每 `CLEANUP_INTERVAL_HOURS` 小时执行一次。

- `seen_posts` 中早于 `SEEN_POSTS_RETENTION_DAYS` 的记录会被删除。
- `notifications` 中早于 `NOTIFICATIONS_RETENTION_DAYS` 的记录会被删除。
- 日志通过 Python `RotatingFileHandler` 轮转；活跃日志文件大小由 `LOG_MAX_BYTES` 控制，备份数量由 `LOG_BACKUP_COUNT` 控制。

默认配置下，活跃日志文件约 100 MB，保留 1 个备份，总日志大小约 200 MB；通知历史默认保留最近 30 天。

## 项目结构

```text
.
├── main.py
├── bot.py
├── monitor.py
├── notifier.py
├── templates.py
├── storage.py
├── config.py
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 许可证

MIT。原始项目许可信息请参考上游项目。
