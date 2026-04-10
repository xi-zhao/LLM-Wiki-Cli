#!/usr/bin/env python3

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
SCRIPTS_DIR = APP_ROOT / "scripts"
FETCH_SCRIPT = SCRIPTS_DIR / "fetch_web_article.py"
RAW_DIR = BASE / "articles" / "raw"
PARSED_DIR = BASE / "articles" / "parsed"
BRIEF_DIR = BASE / "articles" / "briefs"
DEFAULT_MATERIALS_DIR = BASE / "materials" / "web"
SOURCES_INDEX = BASE / "sources" / "index.md"


def load_wechat_module():
    module_path = SCRIPTS_DIR / "ingest_wechat_direct_url.py"
    spec = importlib.util.spec_from_file_location("ingest_wechat_direct_url_shared", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SHARED = load_wechat_module()


def run(cmd: list[str]) -> str:
    return SHARED.run(cmd)


def load_json(path: Path):
    return SHARED.load_json(path)


def read_text(path: Path) -> str:
    return SHARED.read_text(path)


def normalize_url(url: str) -> str:
    return SHARED.normalize_url(url)


def collapse(text: str) -> str:
    return SHARED.collapse(text)


def dedupe_keep_order(items: list[str]) -> list[str]:
    return SHARED.dedupe_keep_order(items)


def short(text: str, limit: int = 120) -> str:
    return SHARED.short(text, limit)


def parse_body_lines(raw_text: str, title: str, source_account: str, publish_time: str) -> list[str]:
    lines = SHARED.parse_body_lines(raw_text, title, source_account, publish_time)
    cleaned = []
    publish_markers = web_publish_markers(publish_time)
    for line in lines:
        if line in publish_markers or is_web_noise_line(line):
            continue
        if is_web_stop_line(line):
            break
        cleaned.append(line)
    return cleaned


def pick_summary(lines: list[str]) -> str:
    return SHARED.pick_summary(lines)


def pick_core_points(lines: list[str], summary: str) -> list[str]:
    return SHARED.pick_core_points(lines, summary)


def pick_facts(lines: list[str], meta: dict, image_count: int) -> list[str]:
    return SHARED.pick_facts(lines, meta, image_count)


def pick_structure(lines: list[str]) -> list[str]:
    return SHARED.pick_structure(lines)


def choose_target(existing: Path | None, canonical: Path, article_id: str):
    return SHARED.choose_target(existing, canonical, article_id)


def backup_existing(path: Path, stamp: str):
    return SHARED.backup_existing(path, stamp)


def find_existing_by_url(directory: Path, normalized_url: str):
    return SHARED.find_existing_by_url(directory, normalized_url)


def update_source_index(entry: dict):
    return SHARED.update_source_index(entry)


def ensure_dirs():
    return SHARED.ensure_dirs()


def write_note(path: Path, content: str):
    return SHARED.write_note(path, content)


def detect_type(title: str, body: str) -> str:
    haystack = f"{title}\n{body}".lower()
    if any(keyword in haystack for keyword in ("tutorial", "step-by-step", "getting started", "installation", "install guide")):
        return "教程"
    if any(keyword in haystack for keyword in ("announces", "launches", "released", "funding", "quarterly results")):
        return "新闻"
    if any(keyword in haystack for keyword in ("research", "study", "paper", "benchmark", "reference architecture", "workflow")):
        return "研究"
    return SHARED.detect_type(title, body)


def confidence_for(completeness: str) -> str:
    return SHARED.confidence_for(completeness)


def reuse_level_for(tags: list[str]) -> str:
    return "high" if any(tag in tags for tag in ("IBM", "量子计算", "AI Agent", "RAG", "知识库")) else "medium"


def ascii_word_present(lower: str, needle: str) -> bool:
    if " " in needle:
        return needle in lower
    if len(needle) >= 8:
        return needle in lower
    return re.search(rf"\b{re.escape(needle)}s?\b", lower) is not None


def web_publish_markers(publish_time: str) -> set[str]:
    value = (publish_time or "").strip()
    markers = {value} if value else set()
    if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return markers
    year, month, day = value.split("-")
    month_num = int(month)
    day_num = int(day)
    short_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    long_months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    markers.add(f"{day_num} {short_months[month_num - 1]} {year}")
    markers.add(f"{day_num} {long_months[month_num - 1]} {year}")
    return markers


def is_web_noise_line(line: str) -> bool:
    compact = collapse(line)
    if not compact:
        return True
    if re.fullmatch(r"\d+\s+minute\s+read", compact, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}", compact):
        return True
    if compact in {"Technical note", "Home", "Date", "Authors", "Topics", "Share", "↳ Blog"}:
        return True
    return False


def is_web_stop_line(line: str) -> bool:
    compact = collapse(line)
    return compact in {"View pricing", "Related posts"} or compact.startswith("Start using our")


def detect_web_tags(title: str, body: str, source_account: str, url: str) -> list[str]:
    haystack = f"{title}\n{body}\n{source_account}\n{url}"
    lower = haystack.lower()
    host = urlparse(url).netloc.lower()
    tags = ["网页"]
    rules = [
        ("IBM", lambda: ascii_word_present(lower, "ibm")),
        ("量子计算", lambda: "quantum" in lower or "量子" in haystack),
        ("HPC", lambda: ascii_word_present(lower, "hpc") or "supercomput" in lower or "超级计算" in haystack),
        ("AI Agent", lambda: ascii_word_present(lower, "agent")),
        ("RAG", lambda: ascii_word_present(lower, "rag")),
        ("知识库", lambda: "knowledge base" in lower or ascii_word_present(lower, "wiki") or "知识库" in haystack),
        ("AI 编程", lambda: "ai coding" in lower or ascii_word_present(lower, "coding") or "编程" in haystack or "code generator" in lower),
    ]
    for tag, matcher in rules:
        if matcher():
            tags.append(tag)
    if "research.ibm.com" in host:
        tags.append("IBM")
    return dedupe_keep_order(tags)[:6]


def detect_web_topics(title: str, body: str) -> list[str]:
    haystack = f"{title}\n{body}"
    lower = haystack.lower()
    topics = []

    if any(keyword in lower for keyword in (
        "knowledge base", "wiki", "research workflow", "research wiki", "obsidian", "markdown repo",
        "科研写作", "文献综述", "研究工作流", "知识库"
    )):
        topics.append("ai-research-writing.md")

    if any(keyword in lower for keyword in (
        "agent", "agents", "skill", "skills", "code generator", "codex", "claude code",
        "prompt", "prompts", "mcp", "harness", "autoresearch", "知识管理员", "代码生成器"
    )):
        topics.append("ai-coding-and-autoresearch.md")

    if any(keyword in lower for keyword in (
        "rag", "notebooklm", "file uploads", "persistent wiki", "incrementally builds",
        "compiled once", "kept current", "cross-references", "synthesis"
    )):
        if "ai-research-writing.md" not in topics:
            topics.append("ai-research-writing.md")
        if "ai-coding-and-autoresearch.md" not in topics:
            topics.append("ai-coding-and-autoresearch.md")

    return dedupe_keep_order(topics)[:3]


def parse_assets(folder: Path) -> list[str]:
    images = load_json(folder / "images.json")
    assets = []
    if isinstance(images, list):
        for item in images:
            if not isinstance(item, dict):
                continue
            value = str(item.get("url", "")).strip()
            if not value:
                continue
            name = Path(urlparse(value).path).name or value
            assets.append(name)
    return dedupe_keep_order(assets)[:5]


def completeness_for(folder: Path, body: str) -> str:
    required = ["meta.json", "page.html", "content.html", "text.txt", "images.json", "assets.md"]
    if all((folder / name).exists() for name in required) and len(body) >= 400:
        return "complete"
    return "partial"


def find_existing_material_folder(normalized_url: str) -> Path | None:
    if not DEFAULT_MATERIALS_DIR.exists():
        return None
    for folder in sorted(DEFAULT_MATERIALS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        meta = load_json(folder / "meta.json")
        value = str(meta.get("url", "")).strip()
        if value and normalize_url(value) == normalized_url:
            return folder.resolve()
    return None


def page_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        return parts[-1].replace(".", "-")
    return parsed.netloc.replace(".", "-")


def write_raw(path: Path, title: str, source_account: str, url: str, publish_time: str, capture_date: str, completeness: str, body_lines: list[str]):
    lines = [
        f"# {title}",
        "",
        "## 元信息",
        "- 来源平台：网页",
        "- 来源形态：web-page",
        f"- 来源账号：{source_account or '待补'}",
        f"- 原文链接：{url}",
        f"- 发布时间：{publish_time or '待补'}",
        f"- 采集时间：{capture_date}",
        f"- 完整度：{completeness}",
        "",
        "## 正文摘录（自动抓取）",
        *body_lines,
        "",
        "## 备注",
        "- 原文已通过直给 URL 的网页抓取流程归档。",
        "- 如需进一步沉淀主题卡或时间线，可在此基础上继续整理。",
    ]
    write_note(path, "\n".join(lines))


def write_parsed(
    path: Path,
    title: str,
    source_account: str,
    author: str,
    url: str,
    publish_time: str,
    capture_date: str,
    tags: list[str],
    article_type: str,
    completeness: str,
    summary: str,
    core_points: list[str],
    facts: list[str],
    structure: list[str],
    folder: Path,
    assets: list[str],
    topics: list[str],
    quotes: list[str],
    brief_path: Path | None = None,
):
    material_root = f"file-organizer/materials/web/{folder.name}"
    topic_wikilinks = [f'[[{Path(topic).stem}]]' for topic in topics] if topics else ['[[topics-moc]]']
    note_lines = [
        '---',
        'type: article',
        'source_type: web',
        f'title: "{title}"',
        f'file_name: "{path.name}"',
        'tags:',
        '  - article',
        '  - obsidian',
        '  - source/web',
        *[f'  - topic/{Path(topic).stem}' for topic in topics],
        '---',
        '',
        f"# 标题：{title}",
        "",
        "## 笔记关系",
        "- Source Index: [[sources-index]]",
        "- Topics MOC: [[topics-moc]]",
        *( [f'- Brief Note: [[{brief_path.stem}]]'] if brief_path else [] ),
        *[f'- Topic Note: {link}' for link in topic_wikilinks],
        "",
        "## 元信息",
        "- 来源平台：网页",
        "- 来源形态：web-page",
        f"- 来源账号 / 站点：{source_account or '待补'}",
        f"- 作者：{author or '待补'}",
        f"- 原文链接：{url}",
        f"- 发布时间：{publish_time or '待补'}",
        f"- 采集时间：{capture_date}",
        f"- 文件名：{path.name}",
        f"- 标签：{', '.join(tags)}",
        f"- 类型：{article_type}",
        f"- 完整度：{completeness}",
        "",
        "## 一句话摘要",
        f"- {summary}",
        "",
        "## 核心结论",
        *[f"{idx}. {point}" for idx, point in enumerate(core_points, start=1)],
        "",
        "## 关键事实 / 证据",
        *[f"- {fact}" for fact in facts],
        "",
        "## 原文结构",
        *[f"### {idx}. {heading}" for idx, heading in enumerate(structure, start=1)],
        "",
        "## 可复用素材",
        "### 可写文章的观点",
        *[f"- {point}" for point in core_points[:2]],
        "- 这篇网页文章适合作为后续研究或写作的证据条目。",
        "",
        "### 可做 PPT 的标题 / 金句",
        f"- {title}",
        "- 从单篇网页文章抽取可复用结论与证据",
        "- 先抓正文，再沉淀为长期知识资产",
        "",
        "### 可引用案例 / 数据",
        *[f"- {fact}" for fact in facts[:3]],
        "",
        "## 本地素材",
        f"- 素材目录：`{material_root}/`",
        f"- 页面HTML：`{material_root}/page.html`",
        f"- 正文HTML：`{material_root}/content.html`",
        f"- 纯文本：`{material_root}/text.txt`",
        f"- 图片清单：`{material_root}/images.json`",
        f"- 素材摘要：`{material_root}/assets.md`",
        "",
        "## 推荐引用素材",
        *([f"- `{asset}`" for asset in assets] if assets else ["- 待补素材推荐"]),
        "",
        "## 风险 / 不确定性 / 待验证",
        "- 当前网页文章卡基于直给 URL 抓取结果与规则抽取生成，重要细节建议回看原文核对。",
        "- 当前自动归档默认先推进到 brief 和 source index；若主题价值较高，可继续人工推进到 topic/timeline。",
        "",
        "## 原文摘录",
        *[f"> {quote}" for quote in quotes],
        "",
        "## 关联主题",
        *([f"- {topic}" for topic in topics] if topics else ["- 待补主题"]),
        "",
        "## 关联笔记（Obsidian）",
        *([f"- [[{Path(topic).stem}]]" for topic in topics] if topics else ["- [[topics-moc]]"]),
        "",
        "## 我的备注",
        "- 这份文章卡由网页直链归档管道自动生成。",
        "- CLI 的结构化结果给 agent 消费，这份 Markdown 文章卡主要给 Obsidian 查看与组织。",
    ]
    write_note(path, "\n".join(note_lines))


def write_brief(path: Path, title: str, summary: str, core_points: list[str], tags: list[str], topics: list[str], parsed_path: Path | None = None):
    importance = next((point for point in core_points if point != summary), core_points[0] if core_points else "这篇内容值得后续继续跟进。")
    topic_wikilinks = [f'[[{Path(topic).stem}]]' for topic in topics] if topics else ['[[topics-moc]]']
    lines = [
        '---',
        'type: brief',
        'source_type: web',
        f'title: "{title}"',
        f'file_name: "{path.name}"',
        'tags:',
        '  - brief',
        '  - obsidian',
        '  - source/web',
        *[f'  - topic/{Path(topic).stem}' for topic in topics],
        '---',
        '',
        f"# Brief｜{title}",
        "",
        "## 笔记关系",
        f"- Article Note: [[{parsed_path.stem if parsed_path else path.stem}]]",
        "- Source Index: [[sources-index]]",
        "- Topics MOC: [[topics-moc]]",
        *[f'- Topic Note: {link}' for link in topic_wikilinks],
        "",
        "## 这篇讲了什么",
        summary,
        "",
        "## 为什么重要",
        importance,
        "",
        "## 可复用点",
        *[f"- {point}" for point in core_points[:3]],
        "",
        "## 关联笔记（Obsidian）",
        *([f"- [[{Path(topic).stem}]]" for topic in topics] if topics else ["- [[topics-moc]]"]),
        "",
        "## 应持续跟踪",
        f"- 与 {', '.join(tags[:3])} 相关的后续案例或标准演进",
        "- 这篇网页文章涉及主题的更多一手资料或官方更新",
        "",
        "## 我的备注",
        "- 这份 brief 由归档流程自动生成，主要给 Obsidian 快速浏览。",
    ]
    write_note(path, "\n".join(lines))


def archive_web_materials(url: str, folder: Path) -> dict:
    ensure_dirs()
    meta = load_json(folder / "meta.json")
    raw_text = read_text(folder / "text.txt")
    normalized_url = normalize_url(url)
    article_id = page_id_from_url(normalized_url)
    capture_date = datetime.now().strftime("%Y-%m-%d")
    publish_time = str(meta.get("publish_time", "")).strip()
    publish_date = publish_time[:10] if len(publish_time) >= 10 else capture_date
    title = str(meta.get("title") or folder.name).strip()
    source_account = str(meta.get("source_account") or "待补").strip()
    author = str(meta.get("author") or source_account or "待补").strip()
    body_lines = parse_body_lines(raw_text, title, source_account, publish_time)
    body = "\n".join(body_lines)
    completeness = completeness_for(folder, body)
    article_type = detect_type(title, body)
    tags = detect_web_tags(title, body, source_account, normalized_url)
    topics = detect_web_topics(title, body)
    summary = pick_summary(body_lines)
    core_points = pick_core_points(body_lines, summary)
    while len(core_points) < 3:
        core_points.append("待补核心结论")
    facts = pick_facts(body_lines, {"source_account": source_account, "create_time": publish_time}, int(meta.get("image_count", 0)))
    structure = pick_structure(body_lines)
    assets = parse_assets(folder)
    quotes = [short(line, 140) for line in body_lines if len(line) >= 24][:2]
    if len(quotes) < 2:
        quotes.append(summary)

    canonical_name = f"{publish_date}_web_article_{article_id}.md"
    raw_existing = find_existing_by_url(RAW_DIR, normalized_url)
    parsed_existing = find_existing_by_url(PARSED_DIR, normalized_url)
    brief_existing = find_existing_by_url(BRIEF_DIR, normalized_url)
    raw_path, raw_renamed = choose_target(raw_existing, RAW_DIR / canonical_name, article_id)
    parsed_path, parsed_renamed = choose_target(parsed_existing, PARSED_DIR / canonical_name, article_id)
    brief_path, brief_renamed = choose_target(brief_existing, BRIEF_DIR / canonical_name, article_id)

    backup_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_files = []
    for candidate in (raw_path, parsed_path, brief_path):
        backup = backup_existing(candidate, backup_stamp)
        if backup:
            backup_files.append(backup)

    write_raw(raw_path, title, source_account, normalized_url, publish_time, capture_date, completeness, body_lines)
    write_parsed(
        parsed_path,
        title,
        source_account,
        author,
        normalized_url,
        publish_time,
        capture_date,
        tags,
        article_type,
        completeness,
        summary,
        core_points,
        facts,
        structure,
        folder,
        assets,
        topics,
        quotes,
        brief_path,
    )
    write_brief(brief_path, title, summary, core_points, tags, topics, parsed_path)

    status = "briefed"
    source_entry = {
        "title": title,
        "source_account": source_account,
        "date": publish_date,
        "url": normalized_url,
        "tags": ", ".join(tags),
        "topics": ", ".join(topics) if topics else "-",
        "type": article_type,
        "completeness": completeness,
        "confidence": confidence_for(completeness),
        "reuse_level": reuse_level_for(tags),
        "followup_needed": "yes",
        "status": status,
    }
    update_source_index(source_entry)

    return {
        "title": title,
        "folder": str(folder),
        "image_count": int(meta.get("image_count", 0)),
        "completeness": completeness,
        "status": status,
        "topics": topics,
        "files": {
            "raw": str(raw_path),
            "parsed": str(parsed_path),
            "brief": str(brief_path),
            "source_index": str(SOURCES_INDEX),
        },
        "renamed_existing_files": [str(path) for path, renamed in ((raw_path, raw_renamed), (parsed_path, parsed_renamed), (brief_path, brief_renamed)) if renamed],
        "backup_files": backup_files,
        "followup_needed": "yes",
    }


def detect_folder(stdout: str) -> Path:
    payload = json.loads(stdout)
    saved_to = payload.get("saved_to")
    if not saved_to:
        raise RuntimeError("fetch script did not return saved_to")
    folder = Path(saved_to).expanduser()
    if not folder.is_dir():
        raise RuntimeError(f"material folder not found: {folder}")
    return folder.resolve()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--base-dir", default=str(DEFAULT_MATERIALS_DIR))
    args = parser.parse_args()

    normalized_url = normalize_url(args.url)
    retrieval_mode = "refetched"
    try:
        fetch_output = run([sys.executable, str(FETCH_SCRIPT), args.url, "--base-dir", args.base_dir])
        folder = detect_folder(fetch_output)
    except RuntimeError:
        folder = find_existing_material_folder(normalized_url)
        if folder is None:
            raise
        retrieval_mode = "reused_existing_materials"

    summary = archive_web_materials(normalized_url, folder)
    print(str(folder))
    print(json.dumps({"status": summary["status"], "url": normalized_url, "retrieval_mode": retrieval_mode, **summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
