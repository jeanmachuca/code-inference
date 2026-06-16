"""
Post-processing of inference responses.
See docs/settings.md § 'Post-processing (postprocessing.py)' for full docs.

Why: Local models via llama.cpp output tool calls as raw JSON text
     (often markdown-wrapped). The @ai-sdk/openai-compatible SDK expects
     a structured tool_calls array. This module bridges that gap.

How: 1. parse_tool_call detects {name, arguments} JSON in content
     2. _get_tool_names extracts allowed names from the request's tools
     3. postprocess_nonstreaming/postprocess_streaming rewrite
        the response into OpenAI format when the name is valid
     4. Hallucinated names (not in the request's tools) are rejected
        and treated as normal text
"""

from __future__ import annotations  # noqa: I001

import json
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any


_MD_FENCE_RE = re.compile(
    r'^```(?:json)?\s*\n?(.*?)\n?```\s*$',
    re.DOTALL,
)


def parse_tool_call(content: str) -> dict[str, Any] | None:
    m = _MD_FENCE_RE.match(content)
    if m:
        content = m.group(1)

    content = content.strip()
    if not content.startswith('{'):
        return None

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(obj, dict):
        return None

    name = obj.get('name')
    arguments = obj.get('arguments')
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(arguments, dict | str) or not arguments:
        return None

    return {'name': name, 'arguments': arguments}


def make_tool_call(tc: dict[str, Any]) -> dict[str, Any]:
    tool_id = 'call_' + uuid.uuid4().hex[:12]
    if isinstance(tc['arguments'], dict):
        args_str = json.dumps(tc['arguments'], ensure_ascii=False)
    else:
        args_str = tc['arguments']
    return {
        'id': tool_id,
        'type': 'function',
        'function': {
            'name': tc['name'],
            'arguments': args_str,
        },
    }


def _get_tool_names(tools: Any = None) -> frozenset[str]:
    if not tools or not isinstance(tools, list):
        return frozenset()
    names: set[str] = set()
    for t in tools:
        if isinstance(t, dict) and t.get('type') == 'function':
            fn = t.get('function')
            if isinstance(fn, dict) and isinstance(fn.get('name'), str) and fn['name']:
                names.add(fn['name'])
    return frozenset(names)


def _common_fields(first_event: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': first_event.get('id', ''),
        'created': first_event.get('created', 0),
        'model': first_event.get('model', ''),
        'system_fingerprint': first_event.get('system_fingerprint', ''),
        'object': 'chat.completion.chunk',
    }


def postprocess_nonstreaming(body: dict[str, Any], tools: Any = None) -> dict[str, Any]:
    if not body.get('choices'):
        return body

    tool_names = _get_tool_names(tools)
    if not tool_names:
        return body

    choice = body['choices'][0]
    msg = choice.get('message', {})
    content = msg.get('content', '') or ''
    if not content.strip():
        return body

    tc = parse_tool_call(content)
    if tc is None:
        return body
    if tc['name'] not in tool_names:
        return body

    tool_call = make_tool_call(tc)

    choice['message'] = {
        'role': 'assistant',
        'content': None,
        'tool_calls': [tool_call],
    }
    choice['finish_reason'] = 'tool_calls'

    return body


def _chunk_str(s: str, size: int = 32) -> list[str]:
    return [s[i : i + size] for i in range(0, len(s), size)]


def _sse(data: dict[str, Any]) -> bytes:
    return f'data: {json.dumps(data, ensure_ascii=False)}\n\n'.encode()


def _infer_is_sse(raw_text: str) -> bool:
    stripped = raw_text.strip()
    return stripped.startswith('data: ') or stripped.startswith('data:[')


def _sse_from_nonstreaming(data: dict[str, Any]) -> bytes:
    data['object'] = 'chat.completion.chunk'
    return _sse(data)


async def postprocess_streaming(
    raw_gen: AsyncIterator[bytes],
    tools: Any = None,
) -> AsyncIterator[bytes]:
    tool_names = _get_tool_names(tools)

    buffer = bytearray()
    async for chunk in raw_gen:
        buffer.extend(chunk)

    raw_bytes = bytes(buffer)
    if not raw_bytes:
        return

    raw_text = raw_bytes.decode('utf-8', errors='replace')

    if not _infer_is_sse(raw_text):
        try:
            body = json.loads(raw_text)
        except json.JSONDecodeError:
            yield raw_bytes
            return
        body = postprocess_nonstreaming(body, tools=tools)
        yield _sse_from_nonstreaming(body)
        yield b'data: [DONE]\n\n'
        return

    if not tool_names:
        yield raw_bytes
        return

    events = raw_text.split('\n\n')

    first_event_data: dict[str, Any] | None = None
    full_content_parts: list[str] = []

    for event in events:
        event = event.strip()
        if not event or event.startswith('data: [DONE]'):
            continue
        if not event.startswith('data: '):
            continue

        json_str = event[len('data: ') :]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        if first_event_data is None:
            first_event_data = data

        choices = data.get('choices', [])
        if not choices:
            continue

        delta = choices[0].get('delta', {})
        content = delta.get('content')
        if content is not None:
            full_content_parts.append(content)

    full_content = ''.join(full_content_parts)
    tc = parse_tool_call(full_content) if full_content.strip() else None

    if tc is None or tc['name'] not in tool_names:
        yield raw_bytes
        return

    meta = _common_fields(first_event_data) if first_event_data else {}
    tool_call = make_tool_call(tc)
    args_str = tool_call['function']['arguments']

    skeleton = {
        **meta,
        'choices': [
            {
                'index': 0,
                'delta': {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [
                        {
                            'index': 0,
                            'id': tool_call['id'],
                            'type': 'function',
                            'function': {
                                'name': tool_call['function']['name'],
                                'arguments': '',
                            },
                        }
                    ],
                },
                'finish_reason': None,
            }
        ],
    }
    yield _sse(skeleton)

    for arg_chunk in _chunk_str(args_str):
        arg_event = {
            **meta,
            'choices': [
                {
                    'index': 0,
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 0,
                                'function': {'arguments': arg_chunk},
                            }
                        ],
                    },
                    'finish_reason': None,
                }
            ],
        }
        yield _sse(arg_event)

    finish = {
        **meta,
        'choices': [
            {
                'index': 0,
                'delta': {},
                'finish_reason': 'tool_calls',
            }
        ],
    }
    yield _sse(finish)
    yield b'data: [DONE]\n\n'
