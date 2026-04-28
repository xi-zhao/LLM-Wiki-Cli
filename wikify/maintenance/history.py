import json
from datetime import datetime, timezone
from pathlib import Path


HISTORY_SCHEMA_VERSION = 'wikify.maintenance-history.v1'


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def write_json(path: Path | str, data: dict) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return str(target)


def append_run(base: Path | str, run_record: dict, dry_run: bool = False) -> str | None:
    if dry_run:
        return None

    history_path = Path(base) / 'sorted' / 'graph-maintenance-history.json'
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding='utf-8'))
        runs = history.setdefault('runs', [])
    else:
        history = {
            'schema_version': HISTORY_SCHEMA_VERSION,
            'created_at': _utc_now(),
            'runs': [],
        }
        runs = history['runs']

    runs.append(run_record)
    history['updated_at'] = _utc_now()
    return write_json(history_path, history)
