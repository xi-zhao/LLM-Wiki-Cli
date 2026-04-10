#!/usr/bin/env python3
import json, os, subprocess
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
KB_BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
BASE = KB_BASE / 'materials' / 'wechat'
PARSED = KB_BASE / 'articles' / 'parsed'

MAPPING = {
    '2026-02-05_ai-research-writing_skills-and-prompts.md': 'GitHub宝藏项目分享：顶尖高校科研者都在用的提示词和Skill一网打尽！',
    '2026-03-23_opus46-autoresearch-flash-attention.md': 'MFU达42%！Opus 4.6+AutoResearch 8小时实现25轮迭代自研高性能GPU算子Flash Attention',
    '2026-03-21_ai-in-theoretical-physics-research.md': 'AI已经进化到可以做理论物理的科研了吗？',
    '2026-03-23_rebar-hvac-quote-ai-productization.md': '拆解一个融了近亿的海外空调报价 AI：ToB AI 产品化的门槛到底在哪里？',
    '2026-03-23_logicbit-quantum-financing.md': '浙大系量子计算「梦之队」再获数亿融资！达晨、经纬联手押注，超导赛道迎爆发期',
    '2026-03-18_quantum-computing-q1-financing.md': '量子计算赛道投资热度再起：2026年Q1融资额逼近2025全年',
    '2026-03-18_15th-five-year-plan-quantum-computing.md': '十五五规划纲要发布_明确研制通用和专用量子计算机',
}

def image_size(path: Path):
    try:
        out = subprocess.check_output(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)], text=True, stderr=subprocess.DEVNULL)
        w = h = 0
        for line in out.splitlines():
            if 'pixelWidth:' in line:
                w = int(line.split(':', 1)[1].strip())
            elif 'pixelHeight:' in line:
                h = int(line.split(':', 1)[1].strip())
        return w, h
    except Exception:
        return 0, 0


def classify(path: Path):
    w, h = image_size(path)
    ratio = (w / h) if w and h else 0
    ext = path.suffix.lower()
    if path.name.startswith('001.'):
        return 'cover', 'likely cover / lead image', w, h
    if ext == '.gif':
        return 'body-supporting', 'animated/supporting visual', w, h
    if w >= 1200 and h >= 800:
        return 'body-core', 'large likely screenshot / chart / key visual', w, h
    if w >= 900 and 0.6 <= ratio <= 1.9:
        return 'body-core', 'substantial in-article visual', w, h
    if w >= 500:
        return 'body-supporting', 'supporting inline visual', w, h
    return 'unknown', 'unclear significance', w, h

for folder in sorted(BASE.iterdir()):
    if not folder.is_dir():
        continue
    images = sorted((folder / 'images').glob('*')) if (folder / 'images').exists() else []
    summary = {'cover': 0, 'body-core': 0, 'body-supporting': 0, 'unknown': 0}
    recommended = []
    lines = ['# Assets', '', '## Summary']
    title = folder.name
    meta = folder / 'meta.json'
    if meta.exists():
        try:
            title = json.loads(meta.read_text()).get('title', title)
        except Exception:
            pass
    lines.append(f'- title: {title}')
    lines.append(f'- total_images: {len(images)}')
    details = []
    for img in images:
        bucket, note, w, h = classify(img)
        summary[bucket] += 1
        details.append((bucket, img.name, note, w, h))
    for key in ['cover', 'body-core', 'body-supporting', 'unknown']:
        lines.append(f'- {key}_count: {summary[key]}')
    lines += ['', '## Notes', '- classification: heuristic, based on file order + image dimensions', '- duplicate handling: normalized in local cleanup pass', '- confidence: medium for cover/large visuals, low otherwise', '', '## Recommended assets']
    priority = [d for d in details if d[0] in ('cover', 'body-core')]
    if not priority:
        priority = details[:3]
    for bucket, name, note, w, h in priority[:6]:
        lines.append(f'- {name} — {bucket}; {note}; {w}x{h}')
        recommended.append(name)
    lines += ['', '## Full asset buckets']
    for key in ['cover', 'body-core', 'body-supporting', 'unknown']:
        lines.append(f'### {key}')
        subset = [d for d in details if d[0] == key]
        if not subset:
            lines.append('- none')
        else:
            for _, name, note, w, h in subset[:20]:
                lines.append(f'- {name} — {note}; {w}x{h}')
        lines.append('')
    (folder / 'assets.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')

    # backlink recommended assets into parsed note
    for parsed_name, folder_name in MAPPING.items():
        if folder_name != folder.name:
            continue
        parsed = PARSED / parsed_name
        if not parsed.exists():
            continue
        text = parsed.read_text(encoding='utf-8')
        block = '## 推荐引用素材\n' + '\n'.join([f'- `{name}`' for name in recommended[:5]]) + '\n\n'
        if '## 推荐引用素材' in text:
            import re
            text = re.sub(r'## 推荐引用素材\n(?:- .*\n)+\n', block, text, flags=re.M)
        else:
            marker = '## 风险 / 不确定性 / 待验证\n'
            if marker in text:
                text = text.replace(marker, block + marker, 1)
            else:
                text += '\n' + block
        parsed.write_text(text, encoding='utf-8')
    print(folder.name)
