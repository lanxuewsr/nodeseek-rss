import os
import re
from dotenv import load_dotenv

load_dotenv()

VERSION = "1.0.1"

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_ID: int = int(os.environ["ALLOWED_USER_ID"])

# How often to poll the RSS feed, in seconds (default: 60, matching feed TTL)
POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "60"))

RSS_BASE_URL: str = os.getenv("RSS_BASE_URL", "https://rss.nodeseek.com/")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/nodeseek-rss.db")

# Flood protection: max individual notifications sent per poll cycle (overflow is summarised)
MAX_NOTIFICATIONS_PER_POLL: int = int(os.getenv("MAX_NOTIFICATIONS_PER_POLL", "10"))

# RSS health: alert user after this many consecutive fetch failures
RSS_FAIL_ALERT_THRESHOLD: int = int(os.getenv("RSS_FAIL_ALERT_THRESHOLD", "3"))

# Keep SQLite tables bounded.
SEEN_POSTS_RETENTION_DAYS: int = int(os.getenv("SEEN_POSTS_RETENTION_DAYS", "30"))
NOTIFICATIONS_RETENTION_DAYS: int = int(os.getenv("NOTIFICATIONS_RETENTION_DAYS", "30"))
CLEANUP_INTERVAL_HOURS: int = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))

# Log file settings. Logs are also emitted to stdout for Docker.
LOG_DIR: str = os.getenv("LOG_DIR", "logs")
LOG_FILE: str = os.getenv("LOG_FILE", "nodeseek-rss.log")
LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(100 * 1024 * 1024)))
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "1"))

# Email notification settings. Only Resend is supported.
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
RESEND_FROM: str = os.getenv("RESEND_FROM", "NodeSeek Monitor <onboarding@resend.dev>")
RESEND_TO: str = os.getenv("RESEND_TO", "")
RESEND_API_URL: str = os.getenv("RESEND_API_URL", "https://api.resend.com/emails")
EMAIL_TIMEOUT_SECONDS: int = int(os.getenv("EMAIL_TIMEOUT_SECONDS", "20"))


def email_configured() -> bool:
    return bool(EMAIL_ENABLED and RESEND_API_KEY and RESEND_TO)


def mask_secret(value: str, head: int = 4, tail: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= head + tail:
        return "***"
    return f"{value[:head]}...{value[-tail:]}"


def validate_config() -> list[str]:
    errors: list[str] = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is empty.")
    elif not re.match(r"^\d+:[A-Za-z0-9_-]{20,}$", TELEGRAM_BOT_TOKEN):
        errors.append(
            "TELEGRAM_BOT_TOKEN format is invalid. It should look like "
            "'123456789:AA...'. Get the full token from @BotFather."
        )

    if ALLOWED_USER_ID <= 0:
        errors.append("ALLOWED_USER_ID must be a positive Telegram user ID.")

    if EMAIL_ENABLED:
        if not RESEND_API_KEY:
            errors.append("EMAIL_ENABLED=true but RESEND_API_KEY is empty.")
        if not RESEND_TO:
            errors.append("EMAIL_ENABLED=true but RESEND_TO is empty.")

    return errors
