from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import aiohttp
from telegram.constants import ParseMode

import config
import templates

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    telegram_ok: bool = False
    email_ok: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.telegram_ok or self.email_ok

    @property
    def status(self) -> str:
        return "sent" if self.success else "failed"


async def send_telegram_with_retry(
    bot,
    chat_id: int,
    text: str,
    max_retries: int = 3,
    **kwargs,
) -> bool:
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error("Telegram send failed after %d retries: %s", max_retries, exc)
    return False


async def send_email(subject: str, html: str, text: str) -> bool:
    if not config.EMAIL_ENABLED:
        logger.info("Email disabled; skipping")
        return False
    if not config.email_configured():
        logger.warning("Email enabled but Resend configuration is incomplete; skipping")
        return False

    payload = {
        "from": config.RESEND_FROM,
        "to": config.RESEND_TO,
        "subject": subject,
        "html": html,
        "text": text,
    }
    timeout = aiohttp.ClientTimeout(total=config.EMAIL_TIMEOUT_SECONDS)
    headers = {
        "Authorization": f"Bearer {config.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(config.RESEND_API_URL, headers=headers, json=payload) as resp:
                if 200 <= resp.status < 300:
                    logger.info("Resend email sent: %s", subject)
                    return True
                body = await resp.text()
                logger.error("Resend email failed: HTTP %s %s", resp.status, body[:1000])
                return False
    except Exception as exc:
        logger.error("Resend email exception: %s", exc)
        return False


async def send_post_notification(bot, post: dict, matched_keywords: list[str]) -> NotificationResult:
    telegram_text = templates.build_telegram_notification(post, matched_keywords)
    email_subject = templates.build_email_subject(post, matched_keywords)
    email_html = templates.build_email_html(post, matched_keywords)
    email_text = templates.build_email_text(post, matched_keywords)

    results = await asyncio.gather(
        send_telegram_with_retry(
            bot,
            config.ALLOWED_USER_ID,
            telegram_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        ),
        send_email(email_subject, email_html, email_text),
        return_exceptions=True,
    )

    result = NotificationResult()
    if isinstance(results[0], Exception):
        result.errors.append(f"telegram: {results[0]}")
    else:
        result.telegram_ok = bool(results[0])

    if isinstance(results[1], Exception):
        result.errors.append(f"email: {results[1]}")
    else:
        result.email_ok = bool(results[1])

    return result


async def send_summary_notification(
    bot,
    notifications: list[tuple[dict, list[str]]],
    sent_count: int,
) -> NotificationResult:
    telegram_text = templates.build_telegram_summary(notifications, sent_count)
    subject, html, text = templates.build_summary_email(notifications, sent_count)

    results = await asyncio.gather(
        send_telegram_with_retry(
            bot,
            config.ALLOWED_USER_ID,
            telegram_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        ),
        send_email(subject, html, text),
        return_exceptions=True,
    )

    result = NotificationResult()
    if isinstance(results[0], Exception):
        result.errors.append(f"telegram: {results[0]}")
    else:
        result.telegram_ok = bool(results[0])

    if isinstance(results[1], Exception):
        result.errors.append(f"email: {results[1]}")
    else:
        result.email_ok = bool(results[1])

    return result
