"""
Telegram bot: command handlers and the recurring RSS-poll job.
"""
from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import monitor
import notifier
import storage

logger = logging.getLogger(__name__)

# ── Module-level state ─────────────────────────────────────────────────────────

# Tracks consecutive RSS fetch failures for health alerting
_rss_fail_count: int = 0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape text for safe inclusion in HTML parse-mode messages."""
    return html.escape(str(text))


def _authorized(update: Update) -> bool:
    return update.effective_user.id == config.ALLOWED_USER_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text(
        "👋 <b>NodeSeek 关键词监控 Bot</b>\n\n"
        "<b>命令列表：</b>\n"
        "/add <code>&lt;关键词&gt;</code> <i>[--regex] [分类]</i>  — 添加监控关键词\n"
        "/remove <code>&lt;关键词&gt;</code>  — 删除关键词（含所有分类）\n"
        "/pause <code>&lt;关键词&gt;</code>  — 暂停关键词（不删除）\n"
        "/resume <code>&lt;关键词&gt;</code>  — 恢复已暂停的关键词\n"
        "/list  — 查看所有监控关键词\n"
        "/history <i>[数量]</i>  — 查看最近推送记录（默认 10 条）\n"
        "/categories  — 查看可用版块分类\n"
        "/status  — 查看 Bot 运行状态\n\n"
        "💡 <i>不填分类则监控全部版块；可多次 /add 同一关键词搭配不同分类。</i>\n"
        "🔍 <i>加 --regex 启用正则匹配，例：/add DMIT.*(CN2|GIA) --regex trade</i>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "用法：/add <code>&lt;关键词&gt;</code> <i>[--regex] [版块]</i>\n\n"
            "<b>普通模式（子串匹配）：</b>\n"
            "  /add DMIT\n"
            "  /add 搬瓦工 trade\n\n"
            "<b>正则模式（--regex，不区分大小写）：</b>\n"
            "  /add DMIT.*(CN2|GIA) --regex\n"
            "    <i>含 CN2 或 GIA 的 DMIT 帖</i>\n"
            "  /add 套餐.*\\d+[Gg] --regex trade\n"
            "    <i>交易版中带容量数字的套餐帖</i>\n"
            "  /add (补货|回归|上新) --regex info\n"
            "    <i>情报版的补货/回归/上新帖</i>\n"
            "  /add ^\\[.*(促销|限时).* --regex\n"
            "    <i>标题开头带促销或限时标签的帖</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    parts = list(context.args)

    # Extract --regex flag
    match_mode = "substring"
    if "--regex" in parts:
        match_mode = "regex"
        parts.remove("--regex")

    # Extract category (last token if it's a known category slug)
    category: Optional[str] = None
    if parts and parts[-1].lower() in monitor.CATEGORIES:
        category = parts.pop().lower()

    keyword = " ".join(parts)

    if not keyword:
        await update.message.reply_text("❌ 关键词不能为空。")
        return

    # Validate regex syntax upfront to give immediate feedback
    if match_mode == "regex":
        try:
            re.compile(keyword)
        except re.error as exc:
            await update.message.reply_text(
                f"❌ 正则表达式无效：<code>{_esc(str(exc))}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

    ok = storage.add_keyword(keyword, category, match_mode)
    if ok:
        cat_str = (
            f"，仅限 <b>{_esc(monitor.CATEGORIES[category])}</b> 版块"
            if category
            else "，监控全部版块"
        )
        mode_str = " 🔍 <i>正则模式</i>" if match_mode == "regex" else ""
        await update.message.reply_text(
            f"✅ 已添加关键词 <code>{_esc(keyword)}</code>{cat_str}{mode_str}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"⚠️ 关键词 <code>{_esc(keyword)}</code>"
            + (f" ({_esc(category)})" if category else "")
            + " 已存在，无需重复添加。",
            parse_mode=ParseMode.HTML,
        )


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "用法：/remove <code>&lt;关键词&gt;</code>\n"
            "将删除该关键词下所有分类的记录。",
            parse_mode=ParseMode.HTML,
        )
        return

    keyword = " ".join(context.args)
    count = storage.remove_keyword(keyword)
    if count:
        await update.message.reply_text(
            f"✅ 已删除关键词 <code>{_esc(keyword)}</code>（共 {count} 条记录）",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"❌ 未找到关键词 <code>{_esc(keyword)}</code>，请用 /list 确认拼写。",
            parse_mode=ParseMode.HTML,
        )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    keywords = storage.list_keywords()
    if not keywords:
        await update.message.reply_text(
            "📋 暂无监控关键词。\n使用 /add 添加第一个。"
        )
        return

    lines = [f"📋 <b>监控关键词（共 {len(keywords)} 条）：</b>\n"]
    for i, kw in enumerate(keywords, 1):
        scope = (
            f"<i>{_esc(monitor.CATEGORIES.get(kw['category'], kw['category']))}</i>"
            if kw["category"]
            else "<i>全部版块</i>"
        )
        mode_tag   = " 🔍" if kw["match_mode"] == "regex" else ""
        status_tag = " ⏸" if not kw["enabled"] else ""
        lines.append(
            f"{i}. <code>{_esc(kw['keyword'])}</code>{mode_tag}{status_tag} — {scope}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "用法：/pause <code>&lt;关键词&gt;</code>\n"
            "暂停监控但不删除，可用 /resume 恢复。",
            parse_mode=ParseMode.HTML,
        )
        return

    keyword = " ".join(context.args)
    count = storage.set_keyword_enabled(keyword, False)
    if count:
        await update.message.reply_text(
            f"⏸ 已暂停关键词 <code>{_esc(keyword)}</code>（{count} 条记录）",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"❌ 未找到关键词 <code>{_esc(keyword)}</code>，请用 /list 确认拼写。",
            parse_mode=ParseMode.HTML,
        )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "用法：/resume <code>&lt;关键词&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    keyword = " ".join(context.args)
    count = storage.set_keyword_enabled(keyword, True)
    if count:
        await update.message.reply_text(
            f"▶️ 已恢复关键词 <code>{_esc(keyword)}</code>（{count} 条记录）",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"❌ 未找到关键词 <code>{_esc(keyword)}</code>，请用 /list 确认拼写。",
            parse_mode=ParseMode.HTML,
        )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    limit = 10
    if context.args:
        try:
            limit = max(1, min(20, int(context.args[0])))
        except ValueError:
            pass

    records = storage.get_history(limit)
    if not records:
        await update.message.reply_text("📭 暂无推送记录。")
        return

    parts = [f"📜 <b>最近 {len(records)} 条推送记录：</b>"]
    for r in records:
        cat_name  = monitor.CATEGORIES.get(r["category"], r["category"])
        sent_at   = r["sent_at"][:16].replace("T", " ")
        kw_tags   = " ".join(
            f"<code>{_esc(k.strip())}</code>" for k in r["keywords"].split(",")
        )
        status_icon = "❌ " if r["status"] == "failed" else ""
        channel_status = (
            f"TG={_esc(r.get('telegram_statuses') or 'n/a')} "
            f"Email={_esc(r.get('email_statuses') or 'n/a')}"
        )
        parts.append(
            f"{status_icon}{kw_tags} · <i>{_esc(cat_name)}</i> · {sent_at}\n"
            f"  <code>{channel_status}</code>\n"
            f"  <a href=\"{r['link']}\">{_esc(r['title'])}</a>"
        )

    await update.message.reply_text(
        "\n\n".join(parts),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    lines = ["🏷 <b>可用版块分类：</b>\n"]
    for slug, name in monitor.CATEGORIES.items():
        lines.append(f"• <code>{slug}</code> — {name}")
    lines.append("\n示例：/add DMIT trade")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    all_keywords = storage.list_keywords()
    active  = sum(1 for kw in all_keywords if kw["enabled"])
    paused  = len(all_keywords) - active
    initialized = storage.get_setting("initialized") == "true"
    email_status = "enabled" if config.EMAIL_ENABLED else "disabled"
    if config.EMAIL_ENABLED and not config.email_configured():
        email_status = "misconfigured"
    log_total_mb = config.LOG_MAX_BYTES * (config.LOG_BACKUP_COUNT + 1) // (1024 * 1024)

    paused_line = f"  ⏸ 已暂停：{paused} 个\n" if paused else ""
    await update.message.reply_text(
        f"✅ <b>NodeSeek RSS v{config.VERSION} 运行正常</b>\n\n"
        f"📊 监控关键词：{active} 个\n"
        f"{paused_line}"
        f"⏱ 轮询间隔：{config.POLL_INTERVAL} 秒\n"
        f"🚦 防洪上限：{config.MAX_NOTIFICATIONS_PER_POLL} 条/轮\n"
        f"📧 Email：<code>{email_status}</code>\n"
        f"🧹 数据保留：seen={config.SEEN_POSTS_RETENTION_DAYS} 天，history={config.NOTIFICATIONS_RETENTION_DAYS} 天\n"
        f"📝 日志总上限：约 {log_total_mb} MB\n"
        f"🌐 RSS 地址：<code>{config.RSS_BASE_URL}</code>\n"
        f"🔄 已初始化：{'是' if initialized else '否（首次轮询后完成）'}",
        parse_mode=ParseMode.HTML,
    )


# ── RSS polling job (runs on bot's event loop via JobQueue) ───────────────────

async def poll_rss(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called every POLL_INTERVAL seconds by PTB's JobQueue.

    Strategy:
    - First run  : seed all current posts as "seen" — no notifications sent.
    - Normal runs: for each new unseen post, check enabled keyword matches.

    Reliability  : each send is retried up to 3× with exponential backoff;
                   failed sends are logged in the notifications table with
                   status='failed' so /history can surface them.

    Flood guard  : at most MAX_NOTIFICATIONS_PER_POLL individual messages are
                   sent per cycle; any overflow is collapsed into one summary.

    RSS health   : consecutive fetch failures increment a counter; once it
                   reaches RSS_FAIL_ALERT_THRESHOLD the user is notified.
    """
    global _rss_fail_count

    # Only consider enabled keywords
    keywords = [kw for kw in storage.list_keywords() if kw["enabled"]]
    if not keywords:
        return

    # Determine which category feeds to request
    need_global   = any(kw["category"] is None for kw in keywords)
    specific_cats: set[str] = {
        kw["category"] for kw in keywords if kw["category"] is not None
    }

    # ── Fetch RSS ──────────────────────────────────────────────────────────────
    entries: dict[int, dict] = {}
    try:
        if need_global:
            for e in await monitor.fetch_entries():
                entries[e["post_id"]] = e
        else:
            for cat in specific_cats:
                for e in await monitor.fetch_entries(cat):
                    entries[e["post_id"]] = e
    except Exception as exc:
        logger.error("RSS fetch failed: %s", exc)
        _rss_fail_count += 1
        if _rss_fail_count == config.RSS_FAIL_ALERT_THRESHOLD:
            alert_post = {
                "post_id": 0,
                "title": f"RSS 拉取连续失败 {_rss_fail_count} 次",
                "link": config.RSS_BASE_URL,
                "category": "system",
                "author": "NodeSeek RSS",
            }
            await notifier.send_post_notification(context.bot, alert_post, ["RSS_FAIL"])
        return

    _rss_fail_count = 0  # Reset on successful fetch

    if not entries:
        return

    # ── First-run: seed without notifying ─────────────────────────────────────
    if storage.get_setting("initialized") != "true":
        logger.info("First poll — seeding %d posts as seen (no notifications)", len(entries))
        storage.mark_many_seen(list(entries.keys()))
        storage.set_setting("initialized", "true")
        return

    # ── Normal run: collect matches ────────────────────────────────────────────
    notifications: list[tuple[dict, list[str]]] = []  # [(post, matched_keywords)]
    new_post_count = 0

    for post_id, post in sorted(entries.items()):
        if storage.is_seen(post_id):
            continue
        storage.mark_seen(post_id)
        new_post_count += 1

        matched = [
            kw["keyword"]
            for kw in keywords
            if (kw["category"] is None or kw["category"] == post["category"])
            and monitor.matches(post["title"], kw["keyword"], kw["match_mode"])
        ]
        if matched:
            notifications.append((post, matched))

    if new_post_count:
        logger.debug(
            "Poll — %d new post(s), %d with keyword match(es)",
            new_post_count, len(notifications),
        )

    if not notifications:
        return

    logger.info("Poll — sending %d notification(s)", len(notifications))

    # ── Flood guard: individual sends up to cap; overflow → one summary ────────
    cap      = config.MAX_NOTIFICATIONS_PER_POLL
    to_send  = notifications[:cap]
    overflow = notifications[cap:]

    sent_count = 0
    for post, matched_kws in to_send:
        result = await notifier.send_post_notification(context.bot, post, matched_kws)
        for kw in matched_kws:
            storage.log_notification(
                post["post_id"], kw, post["title"],
                post["link"], post["category"], post["author"],
                result.status,
                telegram_status="sent" if result.telegram_ok else "failed",
                email_status=(
                    "sent"
                    if result.email_ok
                    else ("skipped" if not config.EMAIL_ENABLED else "failed")
                ),
                error="; ".join(result.errors) if result.errors else None,
            )
        if result.success:
            sent_count += 1
        await asyncio.sleep(0.3)  # Stay within Telegram rate limits

    # Send overflow summary
    if overflow:
        summary_result = await notifier.send_summary_notification(
            context.bot, notifications, len(to_send)
        )
        for post, matched_kws in overflow:
            for kw in matched_kws:
                storage.log_notification(
                    post["post_id"], kw, post["title"],
                    post["link"], post["category"], post["author"],
                    summary_result.status,
                    telegram_status="sent" if summary_result.telegram_ok else "failed",
                    email_status=(
                        "sent"
                        if summary_result.email_ok
                        else ("skipped" if not config.EMAIL_ENABLED else "failed")
                    ),
                    error="; ".join(summary_result.errors) if summary_result.errors else None,
                )

    logger.info(
        "Poll complete — %d sent, %d in overflow summary", sent_count, len(overflow)
    )

    # Periodic DB cleanup
    storage.cleanup_database()
