from __future__ import annotations

import html

import monitor


def _esc(value: object) -> str:
    return html.escape(str(value or ""))


def category_name(category: str) -> str:
    return monitor.CATEGORIES.get(category, category or "未知")


def build_telegram_notification(post: dict, matched_keywords: list[str]) -> str:
    kw_tags = " ".join(f"<code>{_esc(k)}</code>" for k in matched_keywords)
    return (
        f"🔔 <b>关键词提醒</b>  {kw_tags}\n\n"
        f"📌 <b>{_esc(post['title'])}</b>\n"
        f"🏷 {_esc(category_name(post['category']))}\n"
        f"👤 {_esc(post['author'])}\n"
        f"🔗 {post['link']}"
    )


def build_telegram_summary(notifications: list[tuple[dict, list[str]]], sent_count: int) -> str:
    overflow = notifications[sent_count:]
    lines = [
        f"⚠️ <b>本轮匹配 {len(notifications)} 条，已单独推送 {sent_count} 条。"
        f"以下 {len(overflow)} 条已自动汇总：</b>\n"
    ]
    for post, matched_kws in overflow:
        kw_str = " ".join(f"<code>{_esc(k)}</code>" for k in matched_kws)
        lines.append(
            f"• {kw_str} — "
            f"<a href=\"{post['link']}\">{_esc(post['title'])}</a>"
        )
    return "\n".join(lines)


def build_email_subject(post: dict, matched_keywords: list[str]) -> str:
    kw_text = ",".join(matched_keywords)
    title = str(post.get("title") or "NodeSeek keyword match")
    return f"[NodeSeek][{kw_text}] {title}"[:180]


def build_email_text(post: dict, matched_keywords: list[str]) -> str:
    return "\n".join(
        [
            "NodeSeek keyword match",
            "",
            f"Keywords: {', '.join(matched_keywords)}",
            f"Title: {post.get('title', '')}",
            f"Category: {category_name(post.get('category', ''))}",
            f"Author: {post.get('author', '')}",
            f"Link: {post.get('link', '')}",
        ]
    )


def build_email_html(post: dict, matched_keywords: list[str]) -> str:
    title = _esc(post.get("title", ""))
    link = _esc(post.get("link", ""))
    author = _esc(post.get("author", ""))
    category = _esc(category_name(post.get("category", "")))
    keyword_tags = "".join(
        f'<span style="display:inline-block;margin:0 6px 6px 0;padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;background:#f9fafb;color:#111827;font-size:12px">{_esc(k)}</span>'
        for k in matched_keywords
    )

    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f3f4f6;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#111827">
    <div style="max-width:620px;margin:0 auto;padding:28px 14px">
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
        <div style="padding:22px 24px;border-bottom:1px solid #e5e7eb">
          <div style="font-size:13px;color:#4b5563;margin-bottom:10px">NodeSeek 关键词提醒</div>
          <h1 style="font-size:20px;line-height:1.35;margin:0">{title}</h1>
        </div>
        <div style="padding:22px 24px">
          <div style="margin-bottom:14px">{keyword_tags}</div>
          <table style="width:100%;border-collapse:collapse;font-size:14px">
            <tr><td style="width:82px;padding:6px 0;color:#6b7280">分类</td><td style="padding:6px 0">{category}</td></tr>
            <tr><td style="width:82px;padding:6px 0;color:#6b7280">作者</td><td style="padding:6px 0">{author}</td></tr>
          </table>
          <div style="margin-top:20px">
            <a href="{link}" style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;padding:10px 14px;border-radius:6px;font-size:14px">查看帖子</a>
          </div>
          <p style="margin-top:18px;font-size:12px;color:#6b7280;word-break:break-all">{link}</p>
        </div>
      </div>
    </div>
  </body>
</html>"""


def build_summary_email(notifications: list[tuple[dict, list[str]]], sent_count: int) -> tuple[str, str, str]:
    overflow = notifications[sent_count:]
    subject = f"[NodeSeek] 本轮匹配 {len(notifications)} 条，汇总 {len(overflow)} 条"

    text_lines = [
        f"Matched {len(notifications)} posts. Sent individually: {sent_count}. Summary: {len(overflow)}.",
        "",
    ]
    html_rows = []
    for post, matched_kws in overflow:
        kws = ", ".join(matched_kws)
        text_lines.append(f"- [{kws}] {post.get('title', '')} {post.get('link', '')}")
        html_rows.append(
            f"""<tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb"><strong>{_esc(post.get('title', ''))}</strong><br><span style="color:#6b7280;font-size:12px">{_esc(kws)} · {_esc(category_name(post.get('category', '')))}</span></td>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb;text-align:right"><a href="{_esc(post.get('link', ''))}">打开</a></td>
            </tr>"""
        )

    html_body = f"""<!doctype html>
<html>
  <body style="margin:0;background:#f3f4f6;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#111827">
    <div style="max-width:680px;margin:0 auto;padding:28px 14px">
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:22px 24px">
        <h1 style="font-size:20px;margin:0 0 8px">NodeSeek 匹配汇总</h1>
        <p style="font-size:14px;color:#4b5563;margin:0 0 18px">本轮匹配 {len(notifications)} 条，已单独推送 {sent_count} 条，以下 {len(overflow)} 条汇总发送。</p>
        <table style="width:100%;border-collapse:collapse;font-size:14px">{''.join(html_rows)}</table>
      </div>
    </div>
  </body>
</html>"""
    return subject, html_body, "\n".join(text_lines)
