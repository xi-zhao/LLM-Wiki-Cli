#!/usr/bin/env python3
import importlib.util
import os
import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
TOPICS = BASE / 'topics'
OUT = BASE / 'sorted'
SCRIPTS = APP_ROOT / 'scripts'


def extract_section(text: str, heading: str):
    pattern = re.compile(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', re.M | re.S)
    m = pattern.search(text)
    return m.group(1).strip() if m else ''


def bullets(section: str):
    out = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith('- '):
            out.append(line[2:].strip())
    return out


def title_from_topic(text: str, fallback: str):
    m = re.search(r'^# Topic: (.+)$', text, re.M)
    return m.group(1).strip() if m else fallback


def parse_markdown_links(section: str) -> list[tuple[str, str]]:
    return re.findall(r'\[([^\]]+)\]\(([^)]+)\)', section)


def wikilink(target: str, alias: str | None = None) -> str:
    if alias and alias != target:
        return f'[[{target}|{alias}]]'
    return f'[[{target}]]'


def stem_from_link_target(target: str) -> str:
    cleaned = target.split('#', 1)[0]
    return Path(cleaned).stem


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def build_frontmatter(topic_stem: str, title: str, topic_path: Path) -> list[str]:
    return [
        '---',
        'type: digest',
        f'topic: {topic_stem}',
        f'topic_note: "{wikilink(topic_stem, title)}"',
        f'source_topic_path: "{display_path(topic_path)}"',
        'tags:',
        '  - digest',
        '  - obsidian',
        f'  - topic/{topic_stem}',
        '---',
        '',
    ]


def append_bullets(lines: list[str], items: list[str], fallback: str):
    if items:
        for item in items:
            lines.append(f'- {item}')
    else:
        lines.append(f'- {fallback}')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def refresh_navigation_surfaces():
    topic_maintainer = load_module('topic_maintainer_for_digest', SCRIPTS / 'topic_maintainer.py')
    source_index_manager = load_module('source_index_manager_for_digest', SCRIPTS / 'source_index_manager.py')
    topic_maintainer.write_topics_moc()
    source_index_manager.refresh_obsidian_source_index()


def main():
    if len(sys.argv) < 2:
        print('usage: generate_topic_digest.py <topic-file-name>')
        sys.exit(1)
    topic_name = sys.argv[1]
    topic_path = TOPICS / topic_name
    if not topic_path.exists():
        print(f'missing topic file: {topic_path}', file=sys.stderr)
        sys.exit(2)

    text = topic_path.read_text(encoding='utf-8')
    topic_stem = topic_path.stem
    title = title_from_topic(text, topic_name)
    definition = bullets(extract_section(text, '主题定义'))
    core_questions = bullets(extract_section(text, '当前核心问题'))
    stable = bullets(extract_section(text, '稳定结论'))
    observations = extract_section(text, '新增观察')
    evidence = bullets(extract_section(text, '代表性案例 / 证据'))
    outputs = bullets(extract_section(text, '可输出方向'))
    followups = bullets(extract_section(text, '待跟进'))
    related_articles = parse_markdown_links(extract_section(text, '关联文章'))

    one_liner = stable[0] if stable else (definition[0] if definition else f'{title} 正在持续积累，值得做阶段性综述。')

    lines = []
    lines.extend(build_frontmatter(topic_stem, title, topic_path))
    lines.append(f'# 主题综述：{wikilink(topic_stem, title)}')
    lines.append('')
    lines.append('## 摘要判断')
    lines.append(f'- {one_liner}')
    lines.append('')
    lines.append('## 笔记关系')
    lines.append(f'- 主题主笔记：{wikilink(topic_stem, title)}')
    lines.append(f'- Digest 类型：{wikilink(topic_stem)} 的阶段性综述')
    if related_articles:
        lines.append(f'- 关联文章数：{len(related_articles)}')
    lines.append('')
    lines.append('## 为什么现在值得看')
    worth = []
    if stable:
        worth.append('该主题已经沉淀出相对稳定的阶段性判断。')
    if evidence:
        worth.append('已有代表性文章、案例或数据可以直接支撑输出。')
    if followups:
        worth.append('后续仍有持续跟踪空间，不是一次性话题。')
    append_bullets(lines, worth, '该主题已具备从资料堆转成输出草稿的基础。')
    lines.append('')
    lines.append('## 当前核心结论')
    numbered = stable[:5] or ['待补结论']
    for idx, item in enumerate(numbered, start=1):
        lines.append(f'{idx}. {item}')
    lines.append('')
    lines.append('## 支撑证据')
    append_bullets(lines, evidence, '待补代表性证据')
    lines.append('')
    lines.append('## 当前核心问题')
    append_bullets(lines, core_questions[:5], '待补核心问题')
    lines.append('')
    lines.append('## 最近新增观察')
    if observations:
        for line in observations.splitlines()[:12]:
            lines.append(line if line.strip() else '')
    else:
        lines.append('- 待补新增观察')
    lines.append('')
    lines.append('## 关联文章（Obsidian）')
    if related_articles:
        for alias, target in related_articles:
            lines.append(f'- {wikilink(stem_from_link_target(target), alias)}')
    else:
        lines.append('- 待补关联文章')
    lines.append('')
    lines.append('## 适合继续写成什么')
    if outputs:
        for item in outputs:
            lines.append(f'- {item}')
    else:
        lines.append('- 可写文章：待补')
        lines.append('- 可做 PPT：待补')
    lines.append('')
    lines.append('## 还需要继续跟踪什么')
    append_bullets(lines, followups[:5], '待补后续跟踪点')
    lines.append('')
    lines.append('## Source Note')
    lines.append(f'- {wikilink(topic_stem, title)}')
    lines.append(f'- 原始路径：`{display_path(topic_path)}`')

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f'{topic_stem}-digest.md'
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    refresh_navigation_surfaces()
    print(out_path)


if __name__ == '__main__':
    main()
