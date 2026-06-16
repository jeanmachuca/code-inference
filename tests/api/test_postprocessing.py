import json

from app.postprocessing import (
    _get_tool_names,
    make_tool_call,
    parse_tool_call,
    postprocess_nonstreaming,
    postprocess_streaming,
)

_READ_FILE_TOOLS = [
    {'type': 'function', 'function': {'name': 'read_file', 'description': 'Read a file', 'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']}}},
]


def test_parse_tool_call_markdown_json() -> None:
    content = '```json\n{"name": "read_file", "arguments": {"path": "foo.txt"}}\n```'
    result = parse_tool_call(content)
    assert result is not None
    assert result['name'] == 'read_file'
    assert result['arguments'] == {'path': 'foo.txt'}


def test_parse_tool_call_markdown_no_tag() -> None:
    content = '```\n{"name": "read_file", "arguments": {"path": "foo.txt"}}\n```'
    result = parse_tool_call(content)
    assert result is not None
    assert result['name'] == 'read_file'


def test_parse_tool_call_bare_json() -> None:
    content = '{"name": "grep_search", "arguments": {"path": ".", "pattern": "foo"}}'
    result = parse_tool_call(content)
    assert result is not None
    assert result['name'] == 'grep_search'
    assert result['arguments']['pattern'] == 'foo'


def test_parse_tool_call_normal_text() -> None:
    result = parse_tool_call('Hello! How can I help you?')
    assert result is None


def test_parse_tool_call_empty() -> None:
    assert parse_tool_call('') is None
    assert parse_tool_call('   ') is None


def test_parse_tool_call_invalid_json() -> None:
    result = parse_tool_call('{invalid json here}')
    assert result is None


def test_parse_tool_call_missing_name() -> None:
    content = '{"arguments": {"path": "foo.txt"}}'
    result = parse_tool_call(content)
    assert result is None


def test_parse_tool_call_missing_arguments() -> None:
    content = '{"name": "read_file"}'
    result = parse_tool_call(content)
    assert result is None


def test_get_tool_names() -> None:
    tools = [
        {'type': 'function', 'function': {'name': 'read_file'}},
        {'type': 'function', 'function': {'name': 'write_file'}},
    ]
    names = _get_tool_names(tools)
    assert names == frozenset({'read_file', 'write_file'})


def test_get_tool_names_empty() -> None:
    assert _get_tool_names(None) == frozenset()
    assert _get_tool_names([]) == frozenset()
    assert _get_tool_names('not a list') == frozenset()


def test_get_tool_names_skips_malformed() -> None:
    tools = [
        {'type': 'function', 'function': {'name': 'valid'}},
        {'type': 'function', 'function': {'name': ''}},
        {'type': 'function', 'function': {}},
        {'type': 'not_function', 'function': {'name': 'ignored'}},
        {'type': 'function'},
        'not a dict',
    ]
    names = _get_tool_names(tools)
    assert names == frozenset({'valid'})


def test_make_tool_call_structure() -> None:
    tc = {'name': 'read_file', 'arguments': {'path': 'bar.txt'}}
    result = make_tool_call(tc)
    assert result['type'] == 'function'
    assert result['id'].startswith('call_')
    assert len(result['id']) > 10
    assert result['function']['name'] == 'read_file'
    parsed = json.loads(result['function']['arguments'])
    assert parsed == {'path': 'bar.txt'}


def test_postprocess_nonstreaming_tool_call() -> None:
    body = {
        'id': 'test-123',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': '```json\n{"name": "read_file", "arguments": {"path": "x.txt"}}\n```',
            },
            'finish_reason': 'stop',
        }],
    }
    result = postprocess_nonstreaming(body, tools=_READ_FILE_TOOLS)
    msg = result['choices'][0]['message']
    assert msg['content'] is None
    assert len(msg['tool_calls']) == 1
    assert msg['tool_calls'][0]['function']['name'] == 'read_file'
    assert result['choices'][0]['finish_reason'] == 'tool_calls'


def test_postprocess_nonstreaming_no_tools_no_conversion() -> None:
    body = {
        'id': 'test',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': '{"name": "read_file", "arguments": {"path": "x.txt"}}',
            },
            'finish_reason': 'stop',
        }],
    }
    result = postprocess_nonstreaming(body)
    assert result['choices'][0]['message']['content'] is not None
    assert 'tool_calls' not in result['choices'][0]['message']
    assert result['choices'][0]['finish_reason'] == 'stop'


def test_postprocess_nonstreaming_hallucinated_name() -> None:
    body = {
        'id': 'test',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': '{"name": "write_file", "arguments": {"path": "x.txt", "content": "hello"}}',
            },
            'finish_reason': 'stop',
        }],
    }
    result = postprocess_nonstreaming(body, tools=_READ_FILE_TOOLS)
    assert result['choices'][0]['message']['content'] is not None
    assert 'tool_calls' not in result['choices'][0]['message']
    assert result['choices'][0]['finish_reason'] == 'stop'


def test_postprocess_nonstreaming_normal_text_pass_through() -> None:
    body = {
        'id': 'test-456',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': 'Hello! How can I assist you?',
            },
            'finish_reason': 'stop',
        }],
    }
    result = postprocess_nonstreaming(body)
    assert result['choices'][0]['message']['content'] == 'Hello! How can I assist you?'
    assert result['choices'][0]['finish_reason'] == 'stop'


def test_postprocess_nonstreaming_empty_choices() -> None:
    body = {'id': 'test'}
    result = postprocess_nonstreaming(body)
    assert result == body


async def test_postprocess_streaming_tool_call() -> None:
    chunks = [
        b'data: {"id":"x","created":1,"model":"m","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":null},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{"content":"```json\\n{\\"name\\": \\"read_file\\", \\"arguments\\": {\\"path\\": \\"f.txt\\"}}\\n```"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
        b'data: [DONE]\n\n',
    ]

    async def _raw() -> bytes:
        for c in chunks:
            yield c

    results = [line async for line in postprocess_streaming(_raw(), tools=_READ_FILE_TOOLS)]
    output = b''.join(results).decode('utf-8')

    assert 'tool_calls' in output
    assert 'read_file' in output
    assert '"finish_reason": "tool_calls"' in output


async def test_postprocess_streaming_no_tools_no_conversion() -> None:
    chunks = [
        b'data: {"id":"x","created":1,"model":"m","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":null},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{"content":"{\\"name\\": \\"read_file\\", \\"arguments\\": {\\"path\\": \\"f.txt\\"}}"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
        b'data: [DONE]\n\n',
    ]

    async def _raw() -> bytes:
        for c in chunks:
            yield c

    results = [line async for line in postprocess_streaming(_raw())]
    output = b''.join(results).decode('utf-8')

    assert 'tool_calls' not in output
    assert 'read_file' in output


async def test_postprocess_streaming_hallucinated_name() -> None:
    chunks = [
        b'data: {"id":"x","created":1,"model":"m","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":null},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{"content":"{\\"name\\": \\"write_file\\", \\"arguments\\": {\\"path\\": \\"f.txt\\"}}"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
        b'data: [DONE]\n\n',
    ]

    async def _raw() -> bytes:
        for c in chunks:
            yield c

    results = [line async for line in postprocess_streaming(_raw(), tools=_READ_FILE_TOOLS)]
    output = b''.join(results).decode('utf-8')

    assert 'tool_calls' not in output
    assert 'write_file' in output


async def test_postprocess_streaming_non_sse_tool_call() -> None:
    body = json.dumps({
        'id': 'test',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': '{"name": "read_file", "arguments": {"path": "x.txt"}}',
            },
            'finish_reason': 'stop',
        }],
    })

    async def _raw() -> bytes:
        yield body.encode('utf-8')

    results = [line async for line in postprocess_streaming(_raw(), tools=_READ_FILE_TOOLS)]
    output = b''.join(results).decode('utf-8')

    assert 'tool_calls' in output
    assert 'read_file' in output
    assert '"finish_reason": "tool_calls"' in output


async def test_postprocess_streaming_non_sse_normal_text() -> None:
    body = json.dumps({
        'id': 'test',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': 'Hello! How can I help you?',
            },
            'finish_reason': 'stop',
        }],
    })

    async def _raw() -> bytes:
        yield body.encode('utf-8')

    results = [line async for line in postprocess_streaming(_raw())]
    output = b''.join(results).decode('utf-8')

    assert 'Hello! How can I help you?' in output
    assert 'tool_calls' not in output


async def test_postprocess_streaming_normal_text() -> None:
    chunks = [
        b'data: {"id":"x","created":1,"model":"m","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":null},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
        b'data: [DONE]\n\n',
    ]

    async def _raw() -> bytes:
        for c in chunks:
            yield c

    results = [line async for line in postprocess_streaming(_raw())]
    output = b''.join(results).decode('utf-8')

    assert '"content":"Hello"' in output
    assert '"content":" world"' in output
    assert 'tool_calls' not in output
