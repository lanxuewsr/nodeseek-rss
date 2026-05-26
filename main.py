"""
Entry point. Wires together storage, the Telegram Application, and the
recurring RSS-poll job, then starts long-polling.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram.error import InvalidToken
from telegram.ext import Application, CommandHandler

import bot
import config
import storage


def _setup_logging() -> None:
    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        Path(config.LOG_DIR) / config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    for name in ("httpx", "httpcore", "apscheduler", "aiohttp"):
        logging.getLogger(name).setLevel(logging.WARNING)


async def cleanup_job(context) -> None:
    storage.cleanup_database()


def main() -> None:
    _setup_logging()
    log = logging.getLogger(__name__)

    config_errors = config.validate_config()
    if config_errors:
        for error in config_errors:
            log.error("Configuration error: %s", error)
        log.error(
            "Startup stopped. TELEGRAM_BOT_TOKEN=%s",
            config.mask_secret(config.TELEGRAM_BOT_TOKEN),
        )
        raise SystemExit(2)

    storage.init_db()
    log.info("Database ready at %s", config.DATABASE_PATH)

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler(["start", "help"], bot.cmd_start))
    app.add_handler(CommandHandler("add",        bot.cmd_add))
    app.add_handler(CommandHandler("remove",     bot.cmd_remove))
    app.add_handler(CommandHandler("list",       bot.cmd_list))
    app.add_handler(CommandHandler("categories", bot.cmd_categories))
    app.add_handler(CommandHandler("status",     bot.cmd_status))
    app.add_handler(CommandHandler("pause",     bot.cmd_pause))
    app.add_handler(CommandHandler("resume",    bot.cmd_resume))
    app.add_handler(CommandHandler("history",   bot.cmd_history))

    # Schedule the RSS polling job
    app.job_queue.run_repeating(
        bot.poll_rss,
        interval=config.POLL_INTERVAL,
        first=5,  # Small delay so bot is fully ready before first poll
        name="rss_poll",
    )
    app.job_queue.run_repeating(
        cleanup_job,
        interval=max(1, config.CLEANUP_INTERVAL_HOURS) * 3600,
        first=60,
        name="cleanup",
    )

    log.info(
        "Bot started — version=%s  user_id=%d  poll_interval=%ds",
        config.VERSION,
        config.ALLOWED_USER_ID,
        config.POLL_INTERVAL,
    )
    try:
        app.run_polling(drop_pending_updates=True)
    except InvalidToken:
        log.error(
            "Telegram rejected TELEGRAM_BOT_TOKEN=%s. "
            "Open @BotFather, copy the full token, update .env, then restart the container.",
            config.mask_secret(config.TELEGRAM_BOT_TOKEN),
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
