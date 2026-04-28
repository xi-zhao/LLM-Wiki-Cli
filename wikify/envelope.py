import json


def envelope_ok(command: str, result: dict, exit_code: int = 0) -> tuple[dict, int]:
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


def render_pretty(payload: dict) -> str:
    if payload.get('ok'):
        result = payload.get('result', {})
        lines = [
            f"ok: true",
            f"command: {payload.get('command')}",
            f"exit_code: {payload.get('exit_code')}",
        ]
        if isinstance(result, dict):
            for key, value in result.items():
                lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"result: {json.dumps(result, ensure_ascii=False)}")
        return '\n'.join(lines)
    error = payload.get('error', {})
    lines = [
        f"ok: false",
        f"command: {payload.get('command')}",
        f"exit_code: {payload.get('exit_code')}",
    ]
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
