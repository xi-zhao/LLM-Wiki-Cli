#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

SEARCH_DIRS = [
    ('topics', lambda: BASE / 'topics'),
    ('timelines', lambda: BASE / 'timelines'),
    ('briefs', lambda: BASE / 'articles' / 'briefs'),
    ('parsed', lambda: BASE / 'articles' / 'parsed'),
    ('sorted', lambda: BASE / 'sorted'),
]


def discover_app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def discover_base() -> Path:
    env_base = os.environ.get('FOKB_BASE')
    if env_base:
        return Path(env_base).expanduser().resolve()
    return discover_app_root()


APP_ROOT = discover_app_root()
BASE = discover_base()
SCRIPTS = APP_ROOT / 'scripts'
SORTED = BASE / 'sorted'
INGEST = SCRIPTS / 'ingest_any_url.py'
LINT = SCRIPTS / 'wiki_lint.py'
DIGEST = SCRIPTS / 'generate_topic_digest.py'
REVIEW_QUEUE = SORTED / 'review-queue.json'
LAST_PAYLOAD = SORTED / 'last-ingest-payload.json'
LINT_REPORT = SORTED / 'wiki-lint-report.json'
SYSTEM_STATE = SORTED / 'system-state.json'
RESOLVED_REVIEW = SORTED / 'resolved-review.json'
MAINTENANCE_HISTORY = SORTED / 'maintenance-history.json'

EXIT_OK = 0
EXIT_EXEC_ERROR = 1
EXIT_NOT_FOUND = 2
EXIT_QUALITY_GATED = 3
EXIT_REVIEW_REQUIRED = 4
EXIT_CHECK_FAILED = 5
EXIT_DEEP_LINT_WARNING = 6


def ensure_layout():
    required_dirs = [
        BASE,
        SCRIPTS,
        SORTED,
        BASE / 'articles',
        BASE / 'articles' / 'raw',
        BASE / 'articles' / 'parsed',
        BASE / 'articles' / 'briefs',
        BASE / 'topics',
        BASE / 'timelines',
        BASE / 'sources',
        BASE / 'materials',
        BASE / 'archive',
    ]
    for path in required_dirs:
        path.mkdir(parents=True, exist_ok=True)

    defaults = {
        REVIEW_QUEUE: [],
        RESOLVED_REVIEW: [],
        MAINTENANCE_HISTORY: [],
        LAST_PAYLOAD: {},
        LINT_REPORT: {'issues': [], 'suggestions': []},
        SYSTEM_STATE: {},
    }
    for path, default in defaults.items():
        if not path.exists():
            write_json(path, default)


def read_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def envelope_ok(command: str, result: dict, exit_code: int = EXIT_OK) -> tuple[dict, int]:
    return {
        'ok': True,
        'command': command,
        'exit_code': exit_code,
        'result': result,
    }, exit_code


def envelope_error(command: str, code: str, message: str, exit_code: int, retryable: bool = False, details=None) -> tuple[dict, int]:
    return {
        'ok': False,
        'command': command,
        'exit_code': exit_code,
        'error': {
            'code': code,
            'message': message,
            'retryable': retryable,
            'details': details or {},
        },
    }, exit_code


def build_completion(command: str, result: dict) -> dict:
    artifacts = []
    next_actions = []
    summary = f'{command} completed'

    if command in {'writeback', 'synthesize'} and result.get('output_path'):
        artifacts.append(result['output_path'])
        summary = f'{command} completed, output written to {result["output_path"]}'
    elif command == 'promote':
        promotion = result.get('promotion', {}) if isinstance(result.get('promotion'), dict) else {}
        if promotion.get('path'):
            artifacts.append(promotion['path'])
        summary = f'promote completed, target {promotion.get("reason", "processed")}'
    elif command == 'decide' and isinstance(result.get('execution'), dict):
        for item in result['execution'].get('executed', []):
            item_result = item.get('result', {})
            if isinstance(item_result, dict) and item_result.get('path'):
                artifacts.append(item_result['path'])
        summary = f'decide completed with {result["execution"].get("count", 0)} execution step(s)'
    elif command == 'digest' and result.get('output'):
        artifacts.append(result['output'])
        summary = f'digest completed, output written to {result["output"]}'
    elif command in {'ingest', 'reingest'}:
        files = result.get('files', {}) if isinstance(result.get('files'), dict) else {}
        artifacts.extend([path for path in files.values() if isinstance(path, str)])
        next_actions = result.get('next_actions', []) if isinstance(result.get('next_actions'), list) else []
        digest_policy = result.get('digest_policy', {}) if isinstance(result.get('digest_policy'), dict) else {}
        next_actions = [action for action in next_actions if action != 'digest_optional']
        if digest_policy.get('eligible'):
            next_actions.append('digest_optional')
        summary = f'{command} completed for {result.get("title") or result.get("url") or "input"}'
    elif command == 'resolve':
        summary = 'resolve completed, review item removed from queue'

    return {
        'status': 'completed',
        'summary': summary,
        'artifacts': artifacts,
        'next_actions': next_actions,
        'user_message': summary,
    }


def build_digest_policy(result: dict) -> dict:
    quality = result.get('quality', {}) if isinstance(result.get('quality'), dict) else {}
    routing = result.get('routing', {}) if isinstance(result.get('routing'), dict) else {}
    updated_topics = result.get('updated_topics', []) if isinstance(result.get('updated_topics'), list) else []
    next_actions = result.get('next_actions', []) if isinstance(result.get('next_actions'), list) else []

    blocking_reasons = []
    if quality.get('review_required') is True:
        blocking_reasons.append('review_required')
    if result.get('lifecycle_status') != 'integrated':
        blocking_reasons.append('lifecycle_not_integrated')
    if not routing.get('primary_topic'):
        blocking_reasons.append('primary_topic_missing')
    if not updated_topics:
        blocking_reasons.append('no_topic_updates')
    if 'digest_optional' not in next_actions:
        blocking_reasons.append('digest_optional_not_advertised')

    eligible = not blocking_reasons
    return {
        'eligible': eligible,
        'mode': 'auto_eligible' if eligible else 'manual_only',
        'primary_topic': routing.get('primary_topic'),
        'recommended_action': 'digest_optional' if eligible else 'skip_auto_digest',
        'reason': 'eligible_for_auto_digest' if eligible else 'auto_digest_blocked',
        'blocking_reasons': blocking_reasons,
    }


def attach_completion(payload: dict) -> dict:
    if not payload.get('ok'):
        return payload
    result = payload.get('result')
    if isinstance(result, dict):
        result['completion'] = build_completion(payload.get('command', 'unknown'), result)
    return payload


def attach_digest_policy(payload: dict) -> dict:
    if not payload.get('ok'):
        return payload
    if payload.get('command') not in {'ingest', 'reingest'}:
        return payload
    result = payload.get('result')
    if isinstance(result, dict):
        result['digest_policy'] = build_digest_policy(result)
    return payload


def render_pretty(payload: dict) -> str:
    if payload.get('ok'):
        result = payload.get('result', {})
        lines = [f"ok: true", f"command: {payload.get('command')}", f"exit_code: {payload.get('exit_code')}"]
        if isinstance(result, dict):
            for key, value in result.items():
                lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"result: {json.dumps(result, ensure_ascii=False)}")
        return '\n'.join(lines)
    error = payload.get('error', {})
    lines = [f"ok: false", f"command: {payload.get('command')}", f"exit_code: {payload.get('exit_code')}"]
    for key in ['code', 'message', 'retryable']:
        if key in error:
            lines.append(f"error.{key}: {json.dumps(error[key], ensure_ascii=False)}")
    if 'details' in error:
        lines.append(f"error.details: {json.dumps(error['details'], ensure_ascii=False)}")
    return '\n'.join(lines)


def print_output(payload: dict, output_mode: str):
    if output_mode == 'quiet':
        return
    if output_mode == 'pretty':
        print(render_pretty(payload))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def remove_review_item(url: str):
    queue = read_json(REVIEW_QUEUE, [])
    if not isinstance(queue, list):
        return False
    new_queue = [item for item in queue if item.get('url') != url]
    changed = len(new_queue) != len(queue)
    if changed:
        write_json(REVIEW_QUEUE, new_queue)
    return changed


def append_resolved_review(item: dict, resolution: str):
    resolved = read_json(RESOLVED_REVIEW, [])
    if not isinstance(resolved, list):
        resolved = []
    entry = dict(item)
    entry['resolution'] = resolution
    resolved = [r for r in resolved if r.get('url') != entry.get('url')]
    resolved.append(entry)
    write_json(RESOLVED_REVIEW, resolved)


def run_json_command(cmd: list[str], command_name: str) -> tuple[dict, int]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stdout = (proc.stdout or '').strip()
    stderr = (proc.stderr or '').strip()

    if proc.returncode != 0:
        return envelope_error(
            command_name,
            'subcommand_failed',
            stderr or stdout or 'subcommand failed',
            EXIT_EXEC_ERROR,
            retryable=True,
            details={'cmd': cmd, 'stdout': stdout, 'stderr': stderr, 'returncode': proc.returncode},
        )

    try:
        result = json.loads(stdout.splitlines()[-1]) if stdout else {}
    except Exception:
        result = {'stdout': stdout}

    exit_code = EXIT_OK
    if isinstance(result, dict):
        lifecycle = result.get('lifecycle_status')
        quality = result.get('quality', {}) if isinstance(result.get('quality'), dict) else {}
        if lifecycle == 'needs_review':
            exit_code = EXIT_REVIEW_REQUIRED
        elif quality.get('review_required'):
            exit_code = EXIT_QUALITY_GATED

    return envelope_ok(command_name, result, exit_code)


def iter_search_files(scope: str | None = None):
    for name, path_factory in SEARCH_DIRS:
        if scope and scope != name:
            continue
        base = path_factory()
        if not base.exists():
            continue
        for path in sorted(base.rglob('*.md')):
            yield name, path


def search_markdown(query: str, scope: str | None = None, limit: int = 10) -> list[dict]:
    q = query.lower()
    matches = []
    for source_type, path in iter_search_files(scope):
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        text_l = text.lower()
        if q not in text_l and q not in path.name.lower():
            continue
        idx = text_l.find(q)
        snippet = text[max(0, idx - 80): idx + 160].replace('\n', ' ').strip() if idx >= 0 else ''
        score = 2 if q in path.name.lower() else 1
        if idx >= 0:
            score += 1
        matches.append({
            'path': str(path),
            'type': source_type,
            'title': path.stem,
            'score': score,
            'snippet': snippet,
        })
    matches.sort(key=lambda x: (-x['score'], x['path']))
    return matches[:limit]


def cmd_check(args):
    del args
    ensure_layout()
    checks = {
        'base_exists': BASE.exists(),
        'scripts_exists': SCRIPTS.exists(),
        'ingest_script_exists': INGEST.exists(),
        'lint_script_exists': LINT.exists(),
        'digest_script_exists': DIGEST.exists(),
        'review_queue_exists': REVIEW_QUEUE.exists(),
        'resolved_review_exists': RESOLVED_REVIEW.exists(),
        'system_state_exists': SYSTEM_STATE.exists(),
    }
    ok = all(checks.values())
    result = {
        'base': str(BASE),
        'checks': checks,
        'ok': ok,
    }
    if ok:
        return envelope_ok('check', result)
    return envelope_error('check', 'environment_check_failed', 'fokb environment check failed', EXIT_CHECK_FAILED, False, result)


def extract_markdown_links(text: str) -> list[str]:
    return re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)


KNOWN_STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'then', 'than', 'have', 'has', 'had',
    'will', 'would', 'should', 'could', 'about', 'after', 'before', 'through', 'while', 'where', 'when',
    '如何', '什么', '我们', '你们', '他们', '一个', '多个', '可以', '已经', '当前', '后续', '以及', '因为',
    '来源候选', '待补充', 'topic', 'sorted', 'validation', 'decision',
    'parsed', 'ingest', 'timeline', '信号继续完善', '根据后续',
}


TEMPLATE_NOISE_PATTERNS = [
    '初始提升骨架',
    '待补充稳定判断',
    '暂无 parsed 回链',
    '后续补齐',
    '根据后续 ingest',
    '根据后续',
    '信号继续完善',
]


def strip_template_noise(text: str) -> str:
    cleaned = text
    for pattern in TEMPLATE_NOISE_PATTERNS:
        cleaned = cleaned.replace(pattern, ' ')
    cleaned = re.sub(r'\]\([^)]*\)', ' ', cleaned)
    cleaned = re.sub(r'\.{2}/[A-Za-z0-9_./-]+', ' ', cleaned)
    return cleaned


def extract_candidate_concepts(text: str) -> list[str]:
    text = strip_template_noise(text)
    concepts = set()
    for match in re.findall(r'`([^`]{2,40})`', text):
        concepts.add(match.strip())
    for match in re.findall(r'\b[A-Z][A-Za-z0-9_-]{2,}\b', text):
        concepts.add(match.strip())
    for match in re.findall(r'[\u4e00-\u9fffA-Za-z0-9_-]{3,24}', text):
        token = match.strip()
        lower = token.lower()
        if lower in KNOWN_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if token.startswith('wechat-agent-') or token.startswith('quantum-'):
            continue
        if re.fullmatch(r'[a-z]-[a-z0-9-]+', lower):
            continue
        if lower.endswith('-2') or lower.endswith('-3') or lower.endswith('-validation'):
            continue
        concepts.add(token)
    return sorted(concepts)


def collect_existing_concepts(exclude_paths: set[str] | None = None) -> set[str]:
    exclude_paths = exclude_paths or set()
    concepts = set()
    for _, path in iter_search_files():
        if str(path) in exclude_paths:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        concepts.update(extract_candidate_concepts(text))
    return concepts


def build_neighbor_paths(path: Path, object_type: str, text: str) -> list[Path]:
    neighbors = []
    if object_type == 'topics':
        timeline = BASE / 'timelines' / path.name
        if timeline.exists():
            neighbors.append(timeline)
        for link in extract_markdown_links(text):
            if link.startswith('../articles/parsed/'):
                candidate = (path.parent / link).resolve()
                if candidate.exists():
                    neighbors.append(candidate)
    elif object_type == 'timelines':
        topic = BASE / 'topics' / path.name
        if topic.exists():
            neighbors.append(topic)
    elif object_type == 'parsed':
        for link in extract_markdown_links(text):
            if link.startswith('../topics/'):
                candidate = (path.parent / link).resolve()
                if candidate.exists():
                    neighbors.append(candidate)
    elif object_type == 'sorted':
        for link in extract_markdown_links(text):
            candidate = (path.parent / link).resolve()
            if candidate.exists():
                neighbors.append(candidate)
    deduped = []
    seen = set()
    for neighbor in neighbors:
        key = str(neighbor)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(neighbor)
    return deduped


POSITIVE_CLAIM_MARKERS = ['可行', '成立', '支持', '稳定', 'confirmed', 'works', 'valid']
NEGATIVE_CLAIM_MARKERS = ['不可行', '不成立', '失败', '风险', 'broken', 'invalid', 'not work']


def split_sentences(text: str) -> list[str]:
    text = strip_template_noise(text)
    parts = re.split(r'[。！？!?.\n]+', text)
    return [part.strip() for part in parts if part.strip()]


def normalize_subject(subject: str) -> str:
    tokens = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', subject.lower())
    normalized = []
    for token in tokens:
        if token in KNOWN_STOPWORDS:
            continue
        if len(token) <= 1:
            continue
        normalized.append(token)
    return '-'.join(normalized[:4]) or 'unknown-subject'


ALIASES = {
    'openclaw路由': 'openclaw-route',
    'openclaw-router': 'openclaw-route',
    'openclaw': 'openclaw',
    'wechatagent': 'wechat-agent',
    'wechat-agent': 'wechat-agent',
    '路由方案': 'routing-scheme',
}


def canonicalize_subject(subject: str) -> str:
    squashed = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]+', '', subject.lower())
    if squashed in ALIASES:
        return ALIASES[squashed]
    normalized = normalize_subject(subject)
    if normalized in ALIASES:
        return ALIASES[normalized]
    return normalized


def extract_claims(text: str) -> list[dict]:
    claims = []
    for sentence in split_sentences(text):
        polarity = None
        marker = None
        if any(token in sentence for token in NEGATIVE_CLAIM_MARKERS):
            polarity = 'negative'
            marker = next(token for token in NEGATIVE_CLAIM_MARKERS if token in sentence)
        elif any(token in sentence for token in POSITIVE_CLAIM_MARKERS):
            polarity = 'positive'
            marker = next(token for token in POSITIVE_CLAIM_MARKERS if token in sentence)
        if not polarity:
            continue
        concepts = extract_candidate_concepts(sentence)
        if sentence.startswith('- [') or '/sorted/' in sentence:
            continue
        subject = concepts[0] if concepts else sentence[:24]
        claims.append({
            'subject': subject,
            'canonical_subject': canonicalize_subject(subject),
            'polarity': polarity,
            'marker': marker,
            'sentence': sentence,
        })
    return claims


CLAIM_SOURCE_WEIGHTS = {
    'topics': 4,
    'timelines': 3,
    'parsed': 2,
    'briefs': 2,
    'sorted': 1,
    'unknown': 1,
}


def recency_bonus(path: str | None) -> int:
    if not path:
        return 0
    name = Path(path).name
    match = re.match(r'(\d{4}-\d{2}-\d{2})_', name)
    if not match:
        return 0
    date_token = match.group(1)
    if date_token >= '2026-04-01':
        return 1
    return 0


def effective_claim_weight(source_type: str, path: str | None = None) -> int:
    return CLAIM_SOURCE_WEIGHTS.get(source_type, 1) + recency_bonus(path)


def detect_neighbor_tension(text: str, neighbor_entries: list[dict], changed_type: str = 'unknown', changed_path: str | None = None) -> tuple[list[str], list[dict]]:
    tensions = []
    contradictions = []
    claims = extract_claims(text)
    neighbor_claims = []
    for neighbor in neighbor_entries:
        entry_type = neighbor.get('type', 'unknown')
        entry_path = neighbor.get('path')
        for claim in extract_claims(neighbor.get('text', '')):
            claim['source_type'] = entry_type
            claim['source_weight'] = effective_claim_weight(entry_type, entry_path)
            claim['source_path'] = entry_path
            neighbor_claims.append(claim)

    changed_weight = effective_claim_weight(changed_type, changed_path)
    has_positive = any(claim['polarity'] == 'positive' for claim in claims)
    has_negative = any(claim['polarity'] == 'negative' for claim in claims)
    neighbor_positive = any(claim['polarity'] == 'positive' for claim in neighbor_claims)
    neighbor_negative = any(claim['polarity'] == 'negative' for claim in neighbor_claims)
    if has_positive and neighbor_negative:
        tensions.append('changed object is more positive than neighbor evidence')
    if has_negative and neighbor_positive:
        tensions.append('changed object is more negative than neighbor evidence')

    for claim in claims:
        claim['source_type'] = changed_type
        claim['source_weight'] = changed_weight
        for neighbor_claim in neighbor_claims:
            if claim['canonical_subject'] != neighbor_claim['canonical_subject']:
                continue
            if claim['polarity'] == neighbor_claim['polarity']:
                continue
            contradictions.append({
                'subject': claim['subject'],
                'canonical_subject': claim['canonical_subject'],
                'changed_claim': claim,
                'neighbor_claim': neighbor_claim,
                'changed_weight': changed_weight,
                'neighbor_weight': neighbor_claim['source_weight'],
                'baseline_side': 'neighbor' if neighbor_claim['source_weight'] > changed_weight else 'changed',
            })

    return tensions, contradictions


def infer_changed_object_signals(changed_paths: list[str]) -> dict:
    local_signals = []
    local_warnings = []
    local_suggestions = []
    changed_objects = []
    existing_concepts = collect_existing_concepts(set(changed_paths))

    for raw_path in changed_paths:
        path = Path(raw_path)
        if not path.exists() or path.suffix != '.md':
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue

        object_type = path.parts[-2] if len(path.parts) >= 2 else 'unknown'
        links = extract_markdown_links(text)
        concepts = extract_candidate_concepts(text)
        emerging = [concept for concept in concepts if concept not in existing_concepts][:10]
        object_signals = []
        object_warnings = []
        object_suggestions = []
        neighbors = build_neighbor_paths(path, object_type, text)
        neighbor_summaries = []
        neighbor_entries = []

        for neighbor in neighbors:
            try:
                neighbor_text = neighbor.read_text(encoding='utf-8')
            except Exception:
                continue
            neighbor_type = neighbor.parts[-2] if len(neighbor.parts) >= 2 else 'unknown'
            neighbor_summaries.append({
                'path': str(neighbor),
                'type': neighbor_type,
                'title': neighbor.stem,
            })
            neighbor_entries.append({
                'path': str(neighbor),
                'type': neighbor_type,
                'text': neighbor_text,
            })

        if neighbor_summaries:
            object_signals.append('neighbor_context_loaded')
        else:
            object_suggestions.append('changed object has no resolved neighborhood context yet')

        if object_type == 'parsed':
            if '## 关联主题' in text and any('../topics/' in link for link in links):
                object_signals.append('local_topic_linkage_present')
            else:
                object_warnings.append('changed parsed object lacks explicit topic linkage')

        if object_type == 'topics':
            if '## 关联文章' in text and any('../articles/parsed/' in link for link in links):
                object_signals.append('local_topic_backlinks_present')
            elif '## 来源候选' in text and any('../sorted/' in link for link in links):
                object_signals.append('topic_seed_source_present')
            else:
                object_warnings.append('changed topic lacks related article backlinks')

        if object_type == 'timelines':
            expected_topic = BASE / 'topics' / path.name
            if expected_topic.exists():
                object_signals.append('timeline_topic_pair_present')
            else:
                object_suggestions.append(f'changed timeline suggests missing topic pair: {path.name}')

        if object_type == 'sorted':
            if '## Context Excerpts' in text:
                object_signals.append('sorted_context_pack_present')
            else:
                object_suggestions.append('changed sorted output may be too thin for reuse')

        if emerging:
            object_signals.append('emerging_concepts_detected')
            object_suggestions.append(f'emerging concepts in changed object: {", ".join(emerging[:5])}')

        contradiction_markers = []
        for marker in ['但是', '但', '然而', '相反', 'not', 'instead', 'conflict', 'contradict']:
            if marker in text:
                contradiction_markers.append(marker)
        if len(contradiction_markers) >= 2:
            object_signals.append('possible_semantic_tension_detected')
            object_suggestions.append(f'changed object may contain semantic tension markers: {", ".join(sorted(set(contradiction_markers)))}')

        neighbor_tensions, contradictions = detect_neighbor_tension(text, neighbor_entries, object_type, str(path))
        if neighbor_tensions:
            object_signals.append('neighbor_semantic_tension_detected')
            object_suggestions.extend(neighbor_tensions)
        if contradictions:
            object_signals.append('claim_level_contradiction_detected')
            object_warnings.append('changed object has claim-level contradiction with neighbor context')

        changed_objects.append({
            'path': str(path),
            'type': object_type,
            'signals': object_signals,
            'warnings': object_warnings,
            'suggestions': object_suggestions,
            'emerging_concepts': emerging,
            'neighbors': neighbor_summaries,
            'claims': extract_claims(text),
            'contradictions': contradictions,
        })
        local_signals.extend(object_signals)
        local_warnings.extend(object_warnings)
        local_suggestions.extend(object_suggestions)

    return {
        'signals': sorted(set(local_signals)),
        'warnings': local_warnings,
        'suggestions': local_suggestions,
        'changed_objects': changed_objects,
    }


def needs_promotion(changed_object: dict) -> bool:
    object_type = changed_object.get('type')
    signals = set(changed_object.get('signals', []))
    contradictions = changed_object.get('contradictions', [])
    neighbors = changed_object.get('neighbors', [])
    claims = changed_object.get('claims', [])
    if contradictions:
        return False
    if object_type not in {'parsed', 'sorted'}:
        return False
    if 'emerging_concepts_detected' not in signals:
        return False
    if not neighbors and not claims:
        return False
    return True


def synthesize_object_verdict(changed_object: dict) -> str:
    signals = set(changed_object.get('signals', []))
    warnings = changed_object.get('warnings', [])
    contradictions = changed_object.get('contradictions', [])
    if contradictions or 'claim_level_contradiction_detected' in signals:
        return 'conflicted'
    if needs_promotion(changed_object):
        return 'needs_promotion'
    if 'emerging_concepts_detected' in signals:
        return 'emerging'
    if warnings:
        return 'watch'
    if 'sorted_context_pack_present' in signals or 'local_topic_backlinks_present' in signals:
        return 'stable'
    return 'watch'


def synthesize_maintenance_verdict(changed_objects: list[dict], warnings: list[str], suggestions: list[str]) -> str:
    verdicts = {obj.get('verdict', 'watch') for obj in changed_objects}
    if 'conflicted' in verdicts:
        return 'conflicted'
    if 'needs_promotion' in verdicts:
        return 'needs_promotion'
    if 'emerging' in verdicts:
        return 'emerging'
    if warnings:
        return 'watch'
    if suggestions:
        return 'watch'
    if changed_objects and all(v == 'stable' for v in verdicts):
        return 'stable'
    return 'watch'


def build_incremental_maintenance_signals(changed_paths: list[str] | None = None) -> dict:
    changed_paths = changed_paths or []
    deep = run_deep_lint()
    local = infer_changed_object_signals(changed_paths)
    signals = []
    if not deep['parsed_without_topics']:
        signals.append('parsed_topic_linkage_ok')
    if not deep['orphan_topics']:
        signals.append('topic_backlinks_ok')
    if deep['suggestions']:
        signals.append('maintenance_suggestions_present')
    signals.extend(local['signals'])

    touched_types = sorted({Path(path).parts[-2] if len(Path(path).parts) >= 2 else 'unknown' for path in changed_paths})
    changed_objects = local['changed_objects']
    for changed_object in changed_objects:
        changed_object['promotion_candidate'] = needs_promotion(changed_object)
        changed_object['verdict'] = synthesize_object_verdict(changed_object)
        if changed_object['promotion_candidate']:
            changed_object['suggestions'] = changed_object.get('suggestions', []) + [
                'changed object should likely be promoted into a stable topic or timeline artifact'
            ]
    warnings = sorted(set(deep['warnings'] + local['warnings']))
    suggestions = sorted(set(deep['suggestions'] + local['suggestions']))
    verdict = synthesize_maintenance_verdict(changed_objects, warnings, suggestions)
    return {
        'checked': True,
        'scope': 'incremental',
        'verdict': verdict,
        'signals': sorted(set(signals)),
        'suggestions': suggestions,
        'warnings': warnings,
        'changed_paths': changed_paths,
        'touched_types': touched_types,
        'changed_objects': changed_objects,
    }


def normalize_changed_object(changed_object: dict) -> dict:
    normalized = dict(changed_object)
    normalized.setdefault('signals', [])
    normalized.setdefault('warnings', [])
    normalized.setdefault('suggestions', [])
    normalized.setdefault('emerging_concepts', [])
    normalized.setdefault('neighbors', [])
    normalized.setdefault('claims', [])
    normalized.setdefault('contradictions', [])
    normalized.setdefault('promotion_candidate', False)
    normalized.setdefault('verdict', 'watch')
    return normalized


def normalize_maintenance(maintenance: dict) -> dict:
    normalized = dict(maintenance or {})
    normalized.setdefault('checked', True)
    normalized.setdefault('scope', 'incremental')
    normalized.setdefault('verdict', 'watch')
    normalized.setdefault('signals', [])
    normalized.setdefault('suggestions', [])
    normalized.setdefault('warnings', [])
    normalized.setdefault('changed_paths', [])
    normalized.setdefault('touched_types', [])
    changed_objects = normalized.get('changed_objects', [])
    if not isinstance(changed_objects, list):
        changed_objects = []
    normalized['changed_objects'] = [normalize_changed_object(obj) for obj in changed_objects]
    return normalized


def normalize_provenance(provenance: dict | None) -> dict:
    normalized = dict(provenance or {})
    if 'meta' in normalized and isinstance(normalized.get('meta'), dict):
        nested = normalized.pop('meta')
        for key, value in nested.items():
            normalized.setdefault(key, value)
    normalized.setdefault('trigger', None)
    normalized.setdefault('decision', None)
    normalized.setdefault('execution', None)
    normalized.setdefault('execution_mode', None)
    normalized.setdefault('parent_command', None)
    return normalized


def read_maintenance_history() -> list[dict]:
    history = read_json(MAINTENANCE_HISTORY, [])
    if not isinstance(history, list):
        history = []
    normalized_history = []
    changed = False
    for entry in history:
        provenance_source = entry.get('provenance')
        if provenance_source is None and 'meta' in entry:
            provenance_source = entry.get('meta')
        normalized_entry = {
            'command': entry.get('command', 'unknown'),
            'maintenance': normalize_maintenance(entry.get('maintenance', {})),
            'provenance': normalize_provenance(provenance_source),
        }
        if normalized_entry != entry:
            changed = True
        normalized_history.append(normalized_entry)
    if changed:
        write_json(MAINTENANCE_HISTORY, normalized_history)
    return normalized_history


def record_maintenance(command: str, maintenance: dict, provenance: dict | None = None):
    history = read_maintenance_history()
    entry = {
        'command': command,
        'maintenance': normalize_maintenance(maintenance),
        'provenance': normalize_provenance(provenance),
    }
    history.append(entry)
    history = history[-20:]
    write_json(MAINTENANCE_HISTORY, history)


def attach_maintenance(payload: dict, changed_paths: list[str] | None = None, provenance: dict | None = None) -> dict:
    if not payload.get('ok'):
        return payload
    result = payload.get('result')
    if isinstance(result, dict):
        maintenance = build_incremental_maintenance_signals(changed_paths)
        result['maintenance'] = maintenance
        record_maintenance(payload.get('command', 'unknown'), maintenance, provenance)
    return payload


def build_system_state() -> dict:
    review_queue = read_json(REVIEW_QUEUE, [])
    last_payload = read_json(LAST_PAYLOAD, {})
    lint_report = read_json(LINT_REPORT, {})
    resolved_review = read_json(RESOLVED_REVIEW, [])
    maintenance_history = read_maintenance_history()
    state = {
        'base': str(BASE),
        'review_queue_count': len(review_queue) if isinstance(review_queue, list) else 0,
        'resolved_review_count': len(resolved_review) if isinstance(resolved_review, list) else 0,
        'maintenance_history_count': len(maintenance_history) if isinstance(maintenance_history, list) else 0,
        'last_ingest_status': last_payload.get('lifecycle_status'),
        'last_ingest_title': last_payload.get('title'),
        'last_ingest_url': last_payload.get('url'),
        'last_ingest_quality': last_payload.get('quality', {}),
        'lint_summary': {
            'issues_count': len(lint_report.get('issues', [])) if isinstance(lint_report, dict) else None,
            'suggestions_count': len(lint_report.get('suggestions', [])) if isinstance(lint_report, dict) else None,
        },
        'last_maintenance': maintenance_history[-1] if isinstance(maintenance_history, list) and maintenance_history else None,
    }
    write_json(SYSTEM_STATE, state)
    return state


def cmd_init(args):
    del args
    ensure_layout()
    return envelope_ok('init', {'base': str(BASE), 'initialized': True})


def cmd_ingest(args):
    ensure_layout()
    cmd = ['python3', str(INGEST), args.url]
    if args.with_digests:
        cmd.append('--with-digests')
    if args.skip_lint:
        cmd.append('--skip-lint')
    payload, exit_code = run_json_command(cmd, 'ingest')
    changed_paths = []
    if payload.get('ok') and isinstance(payload.get('result'), dict):
        files = payload['result'].get('files', {})
        if isinstance(files, dict):
            changed_paths.extend(str(v) for v in files.values())
    payload = attach_maintenance(payload, changed_paths)
    payload = attach_digest_policy(payload)
    payload = attach_completion(payload)
    build_system_state()
    return payload, exit_code


def run_deep_lint() -> dict:
    topics = [path for _, path in iter_search_files('topics') if not path.name.startswith('_')]
    timelines = [path for _, path in iter_search_files('timelines') if not path.name.startswith('_')]
    parsed_files = [path for _, path in iter_search_files('parsed') if not path.name.startswith('_')]
    sorted_files = [path for _, path in iter_search_files('sorted') if not path.name.startswith('_')]

    topic_names = {path.name for path in topics}
    topic_stems = {path.stem for path in topics}
    timeline_stems = {path.stem for path in timelines}

    issues = []
    warnings = []
    suggestions = []
    orphan_topics = []
    parsed_without_topics = []
    weak_topic_backlinks = []

    parsed_texts = {}
    for path in parsed_files:
        try:
            parsed_texts[path] = path.read_text(encoding='utf-8')
        except Exception:
            parsed_texts[path] = ''

    for path, text in parsed_texts.items():
        if '## 关联主题' not in text:
            parsed_without_topics.append(path.name)
            continue
        if not any(topic_name in text for topic_name in topic_names):
            parsed_without_topics.append(path.name)

    for topic in topics:
        try:
            text = topic.read_text(encoding='utf-8')
        except Exception:
            text = ''
        backlink_count = sum(1 for parsed_text in parsed_texts.values() if topic.name in parsed_text)
        if backlink_count == 0:
            orphan_topics.append(topic.name)
        if '## 关联文章' not in text:
            weak_topic_backlinks.append(topic.name)

    if parsed_without_topics:
        warnings.append('parsed files missing explicit topic linkage')
    if orphan_topics:
        warnings.append('orphan topics detected')
    if weak_topic_backlinks:
        warnings.append('topics missing related article sections')

    for timeline in timelines:
        if timeline.stem not in topic_stems:
            suggestions.append(f'timeline has no matching topic slug: {timeline.name}')

    if len(sorted_files) < max(1, len(topics) // 3):
        suggestions.append('sorted outputs may be too sparse relative to topic count')
    if len(parsed_files) > len(topics) * 3:
        suggestions.append('topic coverage may still be thin relative to parsed volume')

    result = {
        'topic_count': len(topics),
        'timeline_count': len(timelines),
        'parsed_count': len(parsed_files),
        'sorted_count': len(sorted_files),
        'issues': issues,
        'warnings': warnings,
        'suggestions': sorted(set(suggestions)),
        'orphan_topics': orphan_topics,
        'parsed_without_topics': parsed_without_topics,
        'weak_topic_backlinks': weak_topic_backlinks,
    }
    return result


def cmd_lint(args):
    ensure_layout()
    if args.deep:
        result = run_deep_lint()
        exit_code = EXIT_DEEP_LINT_WARNING if (result['warnings'] or result['issues']) else EXIT_OK
        return envelope_ok('lint', result, exit_code)
    return run_json_command(['python3', str(LINT)], 'lint')


def cmd_digest(args):
    ensure_layout()
    proc = subprocess.run(['python3', str(DIGEST), args.topic], capture_output=True, text=True)
    if proc.returncode != 0:
        return envelope_error('digest', 'digest_failed', proc.stderr.strip() or proc.stdout.strip() or 'digest failed', EXIT_EXEC_ERROR, True)
    result = {'topic': args.topic, 'output': (proc.stdout or '').strip().splitlines()[-1] if (proc.stdout or '').strip() else None}
    payload, exit_code = envelope_ok('digest', result)
    if result.get('output'):
        payload = attach_maintenance(payload, [result['output']])
    payload = attach_completion(payload)
    build_system_state()
    return payload, exit_code


def cmd_status(args):
    del args
    ensure_layout()
    return envelope_ok('status', build_system_state())


def build_review_summary(queue: list[dict]) -> dict:
    by_status = {}
    urls = []
    for item in queue:
        status = item.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
        if item.get('url'):
            urls.append(item['url'])
    return {
        'count': len(queue),
        'by_status': by_status,
        'urls': urls,
    }


def cmd_review(args):
    ensure_layout()
    queue = read_json(REVIEW_QUEUE, [])
    if args.url:
        queue = [item for item in queue if item.get('url') == args.url]
    if args.status:
        queue = [item for item in queue if item.get('status') == args.status]

    summary = build_review_summary(queue)

    if args.count:
        return envelope_ok('review', {'count': summary['count']})
    if args.urls_only:
        return envelope_ok('review', {'urls': summary['urls'], 'count': summary['count']})
    if args.summary:
        return envelope_ok('review', summary)
    return envelope_ok('review', {'items': queue, 'count': len(queue), 'summary': summary})


def cmd_reingest(args):
    ensure_layout()
    queue = read_json(REVIEW_QUEUE, [])
    target = None
    if args.url:
        target = next((item for item in queue if item.get('url') == args.url), None)
    elif args.last:
        target = queue[-1] if queue else None
    if not target:
        return envelope_error('reingest', 'review_item_not_found', 'review item not found', EXIT_NOT_FOUND, False)
    cmd = ['python3', str(INGEST), target['url']]
    if args.with_digests:
        cmd.append('--with-digests')
    if args.skip_lint:
        cmd.append('--skip-lint')
    payload, exit_code = run_json_command(cmd, 'reingest')
    changed_paths = []
    if payload.get('ok') and isinstance(payload.get('result'), dict):
        files = payload['result'].get('files', {})
        if isinstance(files, dict):
            changed_paths.extend(str(v) for v in files.values())
    if payload.get('ok') and exit_code == EXIT_OK:
        remove_review_item(target['url'])
        append_resolved_review(target, 'reingest_ok')
    payload = attach_maintenance(payload, changed_paths)
    payload = attach_digest_policy(payload)
    payload = attach_completion(payload)
    build_system_state()
    return payload, exit_code


def cmd_resolve(args):
    ensure_layout()
    queue = read_json(REVIEW_QUEUE, [])
    target = None
    if args.url:
        target = next((item for item in queue if item.get('url') == args.url), None)
    elif args.last:
        target = queue[-1] if queue else None
    if not target:
        return envelope_error('resolve', 'review_item_not_found', 'review item not found', EXIT_NOT_FOUND, False)
    removed = remove_review_item(target['url'])
    append_resolved_review(target, args.reason or 'resolved')
    payload, exit_code = envelope_ok('resolve', {
        'url': target['url'],
        'removed_from_review_queue': removed,
        'resolution': args.reason or 'resolved',
    })
    payload = attach_maintenance(payload, [target['url']])
    payload = attach_completion(payload)
    build_system_state()
    return payload, exit_code


def resolve_show_target(target: str, scope: str | None = None) -> tuple[str | None, Path | None]:
    candidate = Path(target)
    if candidate.exists():
        resolved = candidate.resolve()
        for source_type, path in iter_search_files(scope):
            if path.resolve() == resolved:
                return source_type, path
        return 'path', resolved

    for source_type, path in iter_search_files(scope):
        if path.stem == target or path.name == target:
            return source_type, path
    return None, None


def build_list_entries(scope: str, limit: int | None = None) -> list[dict]:
    entries = []
    for source_type, path in iter_search_files(scope):
        stat = path.stat()
        entries.append({
            'path': str(path),
            'type': source_type,
            'title': path.stem,
            'name': path.name,
            'bytes': stat.st_size,
        })
    if limit is not None:
        entries = entries[:limit]
    return entries


def cmd_search(args):
    ensure_layout()
    matches = search_markdown(args.query, args.scope, args.limit)
    return envelope_ok('search', {
        'query': args.query,
        'scope': args.scope or 'all',
        'count': len(matches),
        'matches': matches,
    })


def cmd_query(args):
    ensure_layout()
    matches = search_markdown(args.query, args.scope, args.limit)
    context = []
    for match in matches:
        path = Path(match['path'])
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        context.append({
            'path': match['path'],
            'type': match['type'],
            'title': match['title'],
            'excerpt': text[: args.max_chars],
        })
    return envelope_ok('query', {
        'query': args.query,
        'scope': args.scope or 'all',
        'count': len(context),
        'context': context,
    })


def cmd_show(args):
    ensure_layout()
    source_type, path = resolve_show_target(args.target, args.scope)
    if not path:
        return envelope_error('show', 'object_not_found', 'show target not found', EXIT_NOT_FOUND, False, {'target': args.target, 'scope': args.scope})
    text = path.read_text(encoding='utf-8')
    result = {
        'target': args.target,
        'path': str(path),
        'type': source_type,
        'title': path.stem,
        'chars': len(text),
    }
    if not args.meta_only:
        result['content'] = text[: args.max_chars]
    return envelope_ok('show', result)


def cmd_list(args):
    ensure_layout()
    entries = build_list_entries(args.scope, args.limit)
    return envelope_ok('list', {
        'scope': args.scope,
        'count': len(entries),
        'items': entries,
    })


def slugify(value: str) -> str:
    cleaned = ''.join(ch.lower() if ch.isalnum() else '-' for ch in value)
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    return cleaned.strip('-') or 'note'


def build_context(query: str, scope: str | None, limit: int, max_chars: int) -> list[dict]:
    matches = search_markdown(query, scope, limit)
    context = []
    for match in matches:
        path = Path(match['path'])
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        context.append({
            'path': match['path'],
            'type': match['type'],
            'title': match['title'],
            'excerpt': text[:max_chars],
        })
    return context


def render_synthesis_markdown(title: str, query: str, scope: str, context: list[dict], mode: str) -> str:
    lines = [
        f'# {title}',
        '',
        f'- Query: `{query}`',
        f'- Scope: `{scope}`',
        f'- Mode: `{mode}`',
        f'- Context count: {len(context)}',
        '',
        '## Source Objects',
        '',
    ]

    for item in context:
        rel_path = os.path.relpath(item['path'], SORTED)
        lines.append(f"- [{item['title']}]({rel_path}) ({item['type']})")

    lines.extend([
        '',
        '## Synthesis',
        '',
    ])

    if mode == 'outline':
        for item in context:
            lines.extend([
                f"- {item['title']} ({item['type']})",
            ])
        lines.extend(['', '## Context Excerpts', ''])
    elif mode == 'bullets':
        for item in context:
            first_line = next((line.strip() for line in item['excerpt'].splitlines() if line.strip()), '')
            lines.extend([
                f"- **{item['title']}**: {first_line}",
            ])
        lines.extend(['', '## Context Excerpts', ''])
    else:
        lines.extend([
            '### Summary',
            f'- Retrieved {len(context)} relevant wiki files for `{query}`.',
            '- Review the excerpts below and promote stable conclusions into topics or timelines as needed.',
            '',
            '## Context Excerpts',
            '',
        ])

    for item in context:
        lines.extend([
            f"### {item['title']}",
            f"- Path: `{item['path']}`",
            f"- Type: `{item['type']}`",
            '',
            item['excerpt'],
            '',
        ])
    return '\n'.join(lines).strip() + '\n'


def cmd_writeback(args):
    ensure_layout()
    context = build_context(args.query, args.scope, args.limit, args.max_chars)

    slug = args.slug or slugify(args.title or args.query)
    output_path = SORTED / f'{slug}.md'
    markdown = render_synthesis_markdown(args.title or args.query, args.query, args.scope or 'all', context, 'context')
    output_path.write_text(markdown, encoding='utf-8')
    payload, exit_code = envelope_ok('writeback', {
        'query': args.query,
        'scope': args.scope or 'all',
        'count': len(context),
        'output_path': str(output_path),
        'slug': slug,
        'mode': 'context',
    })
    payload = attach_maintenance(payload, [str(output_path)])
    payload = attach_completion(payload)
    return payload, exit_code


def cmd_synthesize(args):
    ensure_layout()
    context = build_context(args.query, args.scope, args.limit, args.max_chars)
    slug = args.slug or slugify(args.title or f'{args.query}-{args.mode}')
    output_path = SORTED / f'{slug}.md'
    markdown = render_synthesis_markdown(args.title or args.query, args.query, args.scope or 'all', context, args.mode)
    output_path.write_text(markdown, encoding='utf-8')
    payload, exit_code = envelope_ok('synthesize', {
        'query': args.query,
        'scope': args.scope or 'all',
        'mode': args.mode,
        'count': len(context),
        'output_path': str(output_path),
        'slug': slug,
    })
    payload = attach_maintenance(payload, [str(output_path)])
    payload = attach_completion(payload)
    return payload, exit_code


def cmd_maintenance(args):
    ensure_layout()
    history = read_maintenance_history()
    items = history
    if args.warnings_only:
        items = [item for item in items if item.get('maintenance', {}).get('warnings')]
    if args.last:
        items = items[-1:] if items else []
    if args.limit is not None:
        items = items[-args.limit:]
    return envelope_ok('maintenance', {
        'count': len(items),
        'items': items,
    })


def build_decision_steps(maintenance: dict) -> list[dict]:
    verdict = maintenance.get('verdict', 'watch')
    changed_objects = maintenance.get('changed_objects', [])
    steps = []

    if verdict == 'needs_promotion':
        for obj in changed_objects:
            if not obj.get('promotion_candidate'):
                continue
            target = obj.get('path')
            steps.append({
                'action': 'promote_to_topic_or_timeline',
                'target': target,
                'args': {'path': target},
                'can_execute': True,
                'idempotent': True,
                'retryable': True,
                'reason': 'maintenance verdict indicates stable promotion opportunity',
                'expected_result': 'topic_created_or_already_exists',
            })
        if steps:
            steps.append({
                'action': 'prepare_promotion_candidates',
                'target': None,
                'args': {},
                'can_execute': False,
                'idempotent': True,
                'retryable': False,
                'reason': 'promotion candidates identified for downstream workflow',
                'expected_result': 'promotion_targets_prepared',
            })
    elif verdict == 'conflicted':
        steps.append({
            'action': 'manual_review_required',
            'target': None,
            'args': {},
            'can_execute': False,
            'idempotent': True,
            'retryable': False,
            'reason': 'claim contradiction detected in neighborhood context',
            'expected_result': 'manual_review_ticket',
        })
    elif verdict == 'emerging':
        steps.append({
            'action': 'monitor_and_collect_more_evidence',
            'target': None,
            'args': {},
            'can_execute': False,
            'idempotent': True,
            'retryable': True,
            'reason': 'new concepts detected but promotion threshold not met',
            'expected_result': 'future_evidence_collection',
        })
    else:
        steps.append({
            'action': 'no_immediate_action',
            'target': None,
            'args': {},
            'can_execute': False,
            'idempotent': True,
            'retryable': False,
            'reason': 'no promotion or contradiction action required now',
            'expected_result': 'no_state_change',
        })

    return steps


def build_decision_plan(maintenance: dict) -> dict:
    verdict = maintenance.get('verdict', 'watch')
    steps = build_decision_steps(maintenance)
    actions = [step['action'] for step in steps]
    rationale = [step['reason'] for step in steps]
    promotion_targets = [step['target'] for step in steps if step['action'] == 'promote_to_topic_or_timeline' and step.get('target')]
    return {
        'verdict': verdict,
        'actions': actions,
        'rationale': rationale,
        'promotion_targets': promotion_targets,
        'steps': steps,
    }


def promote_target_to_topic(path: Path) -> dict:
    title = path.stem.replace('-', ' ')
    topic_slug = path.stem
    topic_path = BASE / 'topics' / f'{topic_slug}.md'
    if topic_path.exists():
        return {
            'created': False,
            'path': str(topic_path),
            'reason': 'topic_already_exists',
        }
    topic_path.write_text(
        '\n'.join([
            '---',
            'type: topic',
            f'topic: {topic_slug}',
            'tags:',
            '  - topic',
            '  - obsidian',
            f'  - topic/{topic_slug}',
            '---',
            '',
            f'# Topic: {title}',
            '',
            '## 笔记关系',
            f'- Topic Note: [[{topic_slug}|{title}]]',
            f'- Digest Note: [[{topic_slug}-digest]]',
            '- MOC: [[topics-moc]]',
            '',
            '## 来源候选',
            f'- [{path.stem}](../sorted/{path.name})',
            '',
            '## 稳定结论',
            '- 初始提升骨架，待补充稳定判断。',
            '',
            '## 关联文章',
            '- 暂无 parsed 回链，后续补齐。',
            '',
            '## 关联笔记（Obsidian）',
            '- 待补关联笔记。',
            '',
            '## 待跟进',
            '- 根据后续 ingest / parsed / timeline 信号继续完善。',
            '',
        ]),
        encoding='utf-8',
    )
    return {
        'created': True,
        'path': str(topic_path),
        'reason': 'topic_created_from_sorted',
    }


def cmd_promote(args):
    ensure_layout()
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        return envelope_error('promote', 'object_not_found', 'promotion source not found', EXIT_NOT_FOUND, False, {'path': args.path})
    result = promote_target_to_topic(target_path)
    payload, exit_code = envelope_ok('promote', {
        'source_path': str(target_path),
        'target_type': 'topic',
        'promotion': result,
    })
    payload = attach_maintenance(payload, [str(target_path), result['path']])
    payload = attach_completion(payload)
    build_system_state()
    return payload, exit_code


def build_execution_entry(step: dict, status: str, reason: str, result: dict | None = None, artifacts: dict | None = None, state_change: dict | None = None, side_effects: list[str] | None = None) -> dict:
    return {
        'action': step.get('action'),
        'target': step.get('target'),
        'status': status,
        'reason': reason,
        'result': result or {},
        'artifacts': artifacts or {'created': [], 'updated': [], 'skipped': []},
        'state_change': state_change or {},
        'side_effects': side_effects or [],
    }


def execute_decision_plan(plan: dict) -> dict:
    executed = []
    for step in plan.get('steps', []):
        action = step.get('action')
        target = step.get('target')
        if not step.get('can_execute'):
            executed.append(build_execution_entry(
                step,
                'skipped_non_executable',
                'step_marked_non_executable',
                state_change={'executed': False},
            ))
            continue
        if action == 'promote_to_topic_or_timeline':
            target_path = Path(target)
            if not target_path.exists():
                executed.append(build_execution_entry(
                    step,
                    'missing',
                    'target_not_found',
                    state_change={'executed': False},
                ))
                continue
            result = promote_target_to_topic(target_path)
            target_artifact = result.get('path')
            created = bool(result.get('created'))
            executed.append(build_execution_entry(
                step,
                'promoted' if created else 'skipped',
                result.get('reason', 'promotion_executed'),
                result=result,
                artifacts={
                    'created': [target_artifact] if created and target_artifact else [],
                    'updated': [],
                    'skipped': [target_artifact] if (not created and target_artifact) else [],
                },
                state_change={
                    'executed': True,
                    'created_topic': created,
                },
                side_effects=['topic_written'] if created else ['idempotent_noop'],
            ))
            continue
        executed.append(build_execution_entry(
            step,
            'unsupported_action',
            'action_not_implemented',
            state_change={'executed': False},
        ))
    return {
        'executed': executed,
        'count': len(executed),
        'mode': 'decision_execute',
    }


def resolve_decision_target(args, history: list[dict]) -> tuple[dict, dict]:
    if args.maintenance_path:
        maintenance = build_incremental_maintenance_signals([str(Path(args.maintenance_path).resolve())])
        return normalize_maintenance(maintenance), {
            'source': 'maintenance_path',
            'maintenance_path': str(Path(args.maintenance_path).resolve()),
        }
    if args.last:
        entry = history[-1] if history else {'maintenance': {}}
        return normalize_maintenance(entry.get('maintenance', {})), {
            'source': 'history_last',
            'history_command': entry.get('command'),
        }
    entry = history[-1] if history else {'maintenance': {}}
    return normalize_maintenance(entry.get('maintenance', {})), {
        'source': 'history_last_default',
        'history_command': entry.get('command'),
    }


def cmd_decide(args):
    ensure_layout()
    history = read_maintenance_history()
    target, decision_source = resolve_decision_target(args, history)
    plan = build_decision_plan(target)
    result = {
        'maintenance': target,
        'decision': plan,
        'decision_source': decision_source,
    }
    if args.execute:
        execution = execute_decision_plan(plan)
        result['execution'] = execution
        executed_paths = []
        for item in execution.get('executed', []):
            item_result = item.get('result', {})
            if item.get('target'):
                executed_paths.append(item['target'])
            if isinstance(item_result, dict) and item_result.get('path'):
                executed_paths.append(item_result['path'])
        payload, exit_code = envelope_ok('decide', result)
        payload = attach_maintenance(payload, executed_paths, {
            'trigger': 'decide --execute',
            'parent_command': 'decide',
            'execution_mode': 'decision_execute',
            'decision': plan,
            'execution': execution,
            'decision_source': decision_source,
        })
        payload = attach_completion(payload)
        build_system_state()
        return payload, exit_code
    payload, exit_code = envelope_ok('decide', result)
    payload = attach_completion(payload)
    return payload, exit_code


def cmd_stats(args):
    del args
    ensure_layout()
    system = build_system_state()
    counts = {scope: len(build_list_entries(scope)) for scope, _ in SEARCH_DIRS}
    recent_sorted = build_list_entries('sorted', limit=5)
    result = {
        'base': str(BASE),
        'counts': counts,
        'review_queue_count': system.get('review_queue_count'),
        'resolved_review_count': system.get('resolved_review_count'),
        'maintenance_history_count': system.get('maintenance_history_count'),
        'last_ingest': {
            'status': system.get('last_ingest_status'),
            'title': system.get('last_ingest_title'),
            'url': system.get('last_ingest_url'),
        },
        'last_maintenance': system.get('last_maintenance'),
        'lint_summary': system.get('lint_summary'),
        'recent_sorted': recent_sorted,
    }
    return envelope_ok('stats', result)


def cmd_state(args):
    del args
    ensure_layout()
    state = {
        'system': build_system_state(),
        'review_queue': read_json(REVIEW_QUEUE, []),
        'resolved_review': read_json(RESOLVED_REVIEW, []),
        'maintenance_history': read_maintenance_history(),
        'last_ingest_payload': read_json(LAST_PAYLOAD, {}),
        'lint_report': read_json(LINT_REPORT, {}),
    }
    return envelope_ok('state', state)


def build_parser():
    parser = argparse.ArgumentParser(
        prog='fokb',
        description='File Organizer Knowledge Base CLI, agent-facing entrypoint',
    )
    parser.add_argument('--output', choices=['json', 'pretty', 'quiet'], default='json', help='Output mode')

    sub = parser.add_subparsers(dest='command', required=True)

    p_init = sub.add_parser('init', help='Initialize KB directory layout and state files')
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser('check', help='Check environment and required files')
    p_check.set_defaults(func=cmd_check)

    p_ingest = sub.add_parser('ingest', help='Ingest a URL into the knowledge base')
    p_ingest.add_argument('url')
    p_ingest.add_argument('--with-digests', action='store_true')
    p_ingest.add_argument('--skip-lint', action='store_true')
    p_ingest.set_defaults(func=cmd_ingest)

    p_lint = sub.add_parser('lint', help='Run knowledge base lint')
    p_lint.add_argument('--deep', action='store_true')
    p_lint.set_defaults(func=cmd_lint)

    p_digest = sub.add_parser('digest', help='Generate digest for a topic file')
    p_digest.add_argument('topic', help='Topic file name, e.g. ai-coding-and-autoresearch.md')
    p_digest.set_defaults(func=cmd_digest)

    p_status = sub.add_parser('status', help='Show machine-readable KB status summary')
    p_status.set_defaults(func=cmd_status)

    p_review = sub.add_parser('review', help='Inspect review queue items')
    p_review.add_argument('--url')
    p_review.add_argument('--status')
    p_review.add_argument('--summary', action='store_true')
    p_review.add_argument('--count', action='store_true')
    p_review.add_argument('--urls-only', action='store_true')
    p_review.set_defaults(func=cmd_review)

    p_reingest = sub.add_parser('reingest', help='Re-run ingest for a review item')
    p_reingest.add_argument('--url')
    p_reingest.add_argument('--last', action='store_true')
    p_reingest.add_argument('--with-digests', action='store_true')
    p_reingest.add_argument('--skip-lint', action='store_true')
    p_reingest.set_defaults(func=cmd_reingest)

    p_resolve = sub.add_parser('resolve', help='Resolve and dequeue a review item')
    p_resolve.add_argument('--url')
    p_resolve.add_argument('--last', action='store_true')
    p_resolve.add_argument('--reason')
    p_resolve.set_defaults(func=cmd_resolve)

    p_search = sub.add_parser('search', help='Search compiled markdown wiki files')
    p_search.add_argument('query')
    p_search.add_argument('--scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_search.add_argument('--limit', type=int, default=10)
    p_search.set_defaults(func=cmd_search)

    p_query = sub.add_parser('query', help='Gather query context from compiled wiki files')
    p_query.add_argument('query')
    p_query.add_argument('--scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_query.add_argument('--limit', type=int, default=5)
    p_query.add_argument('--max-chars', type=int, default=1200)
    p_query.set_defaults(func=cmd_query)

    p_show = sub.add_parser('show', help='Show one wiki object by logical id or path')
    p_show.add_argument('target')
    p_show.add_argument('--scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_show.add_argument('--max-chars', type=int, default=4000)
    p_show.add_argument('--meta-only', action='store_true')
    p_show.set_defaults(func=cmd_show)

    p_list = sub.add_parser('list', help='List wiki objects by scope')
    p_list.add_argument('scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_list.add_argument('--limit', type=int)
    p_list.set_defaults(func=cmd_list)

    p_writeback = sub.add_parser('writeback', help='Write query context into sorted markdown')
    p_writeback.add_argument('query')
    p_writeback.add_argument('--title')
    p_writeback.add_argument('--slug')
    p_writeback.add_argument('--scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_writeback.add_argument('--limit', type=int, default=5)
    p_writeback.add_argument('--max-chars', type=int, default=1200)
    p_writeback.set_defaults(func=cmd_writeback)

    p_synthesize = sub.add_parser('synthesize', help='Create structured synthesis markdown from query context')
    p_synthesize.add_argument('query')
    p_synthesize.add_argument('--title')
    p_synthesize.add_argument('--slug')
    p_synthesize.add_argument('--scope', choices=['topics', 'timelines', 'briefs', 'parsed', 'sorted'])
    p_synthesize.add_argument('--limit', type=int, default=5)
    p_synthesize.add_argument('--max-chars', type=int, default=1200)
    p_synthesize.add_argument('--mode', choices=['summary', 'outline', 'bullets'], default='summary')
    p_synthesize.set_defaults(func=cmd_synthesize)

    p_maintenance = sub.add_parser('maintenance', help='Inspect maintenance history')
    p_maintenance.add_argument('--last', action='store_true')
    p_maintenance.add_argument('--warnings-only', action='store_true')
    p_maintenance.add_argument('--limit', type=int)
    p_maintenance.set_defaults(func=cmd_maintenance)

    p_decide = sub.add_parser('decide', help='Build next-step decision plan from maintenance verdict')
    p_decide.add_argument('--last', action='store_true')
    p_decide.add_argument('--maintenance-path', help='Build decision from an explicit changed object path instead of history tail')
    p_decide.add_argument('--execute', action='store_true')
    p_decide.set_defaults(func=cmd_decide)

    p_promote = sub.add_parser('promote', help='Promote a candidate object into a stable topic artifact')
    p_promote.add_argument('path')
    p_promote.set_defaults(func=cmd_promote)

    p_stats = sub.add_parser('stats', help='Show product-level KB overview stats')
    p_stats.set_defaults(func=cmd_stats)

    p_state = sub.add_parser('state', help='Show full machine-readable control state')
    p_state.set_defaults(func=cmd_state)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    payload, exit_code = args.func(args)
    print_output(payload, args.output)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
