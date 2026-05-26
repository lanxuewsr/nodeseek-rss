# NodeSeek RSS

NodeSeek RSS is a private monitor for [NodeSeek](https://www.nodeseek.com/) RSS feeds. It watches new posts, matches configured keywords, and sends notifications through Telegram and Resend email.

Version: `1.0.0`

This project is developed on top of [n-AChegYag/nodeseek-keywords](https://github.com/n-AChegYag/nodeseek-keywords). The original Telegram keyword monitor was used as the base, then Resend email notification, unified channel status, log rotation, database retention cleanup, and multi-arch Docker packaging were added.

## Features

- Keyword monitoring with case-insensitive substring matching.
- Regex keyword matching with validation.
- Category filtering for NodeSeek boards.
- Telegram command management.
- Telegram and Resend email notifications.
- Per-channel notification history.
- Flood guard with summary notification.
- First-run silence to avoid pushing old posts.
- SQLite persistence and duplicate prevention.
- RSS health alerts.
- Configurable database cleanup.
- Rotating log file cleanup with a size cap.
- Linux direct run and Docker deployment.
- Docker image supports `linux/amd64` and `linux/arm64`.

## Supported Categories

| Slug | Name |
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

## Quick Start With Docker

```bash
docker run -d \
  --name nodeseek-rss \
  --restart unless-stopped \
  --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  lanxuewsr/nodeseek-rss:latest
```

Or use Compose:

```bash
cp .env.example .env
# edit .env
docker compose up -d
```

## Direct Linux Run

Python 3.11+ is recommended.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
python main.py
```

## Configuration

| Variable | Required | Default | Description |
|---|---:|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram Bot token from BotFather |
| `ALLOWED_USER_ID` | Yes | - | Telegram user ID allowed to control the bot |
| `RSS_BASE_URL` | No | `https://rss.nodeseek.com/` | NodeSeek RSS URL |
| `POLL_INTERVAL` | No | `60` | RSS poll interval in seconds |
| `MAX_NOTIFICATIONS_PER_POLL` | No | `10` | Max individual notifications per poll |
| `RSS_FAIL_ALERT_THRESHOLD` | No | `3` | Send health alert after N consecutive RSS failures |
| `DATABASE_PATH` | No | `data/nodeseek-rss.db` | SQLite database path |
| `SEEN_POSTS_RETENTION_DAYS` | No | `30` | Keep seen-post dedupe records for N days |
| `NOTIFICATIONS_RETENTION_DAYS` | No | `30` | Keep notification history for N days |
| `CLEANUP_INTERVAL_HOURS` | No | `24` | Run cleanup every N hours |
| `LOG_DIR` | No | `logs` | Log directory |
| `LOG_FILE` | No | `nodeseek-rss.log` | Log file name |
| `LOG_MAX_BYTES` | No | `104857600` | Max active log file size, default 100 MB |
| `LOG_BACKUP_COUNT` | No | `1` | Number of rotated log backups |
| `EMAIL_ENABLED` | No | `true` | Enable Resend email notification |
| `RESEND_API_KEY` | If email enabled | - | Resend API key |
| `RESEND_FROM` | If email enabled | `NodeSeek Monitor <onboarding@resend.dev>` | Email sender |
| `RESEND_TO` | If email enabled | - | Email recipient |
| `RESEND_API_URL` | No | `https://api.resend.com/emails` | Resend API endpoint |
| `EMAIL_TIMEOUT_SECONDS` | No | `20` | Email request timeout |

SMTP2HTTP is intentionally not included. Email is sent through Resend only.

## Telegram Commands

| Command | Description |
|---|---|
| `/start` `/help` | Show help |
| `/add <keyword> [--regex] [category]` | Add keyword |
| `/remove <keyword>` | Remove keyword from all categories |
| `/pause <keyword>` | Pause keyword |
| `/resume <keyword>` | Resume keyword |
| `/list` | List keywords |
| `/history [limit]` | Show recent notification history |
| `/categories` | Show category slugs |
| `/status` | Show runtime status, email status, and cleanup settings |

## Keyword Examples

```text
/add DMIT
/add 搬瓦工 trade
/add DMIT.*(CN2|GIA) --regex
/add (补货|回归|上新) --regex info
```

## Docker Images

Published tags:

```text
lanxuewsr/nodeseek-rss:1.0.0
lanxuewsr/nodeseek-rss:latest
```

Manual multi-arch build:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t lanxuewsr/nodeseek-rss:1.0.0 \
  -t lanxuewsr/nodeseek-rss:latest \
  --push .
```

## Data Retention

The cleanup job runs every `CLEANUP_INTERVAL_HOURS` hours.

- `seen_posts` rows older than `SEEN_POSTS_RETENTION_DAYS` are deleted.
- `notifications` rows older than `NOTIFICATIONS_RETENTION_DAYS` are deleted.
- Log files are rotated by Python `RotatingFileHandler`; the active file is capped by `LOG_MAX_BYTES`, and backup count is controlled by `LOG_BACKUP_COUNT`.

With defaults, the active log file is capped at about 100 MB with one rotated backup, so log files stay around 200 MB total. Notification history keeps the latest 30 days.

## Project Structure

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

## License

MIT. See the upstream project for original licensing context.
