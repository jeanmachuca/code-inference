from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.postprocessing import postprocess_nonstreaming, postprocess_streaming
from app.prompt import process_messages

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title='code_inference AI API', version='0.1.0')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.middleware('http')
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request.state.request_id = req_id
    start = time.time()
    method = request.method
    path = request.url.path
    client = request.client.host if request.client else 'unknown'
    logger.info('request %s %s %s client=%s', method, path, req_id, client)
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        'response %s %s status=%s duration=%.3f',
        method,
        path,
        response.status_code,
        duration,
    )
    response.headers['X-Request-Id'] = req_id
    return response


ContentItem = dict[str, Any]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='allow')
    role: str
    content: str | list[ContentItem] | None = None


def extract_text(content: str | list[ContentItem] | None) -> str:
    if isinstance(content, list):
        return ''.join(item.get('text', '') for item in content if item.get('type') == 'text')
    return content or ''


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra='allow')
    model: str = Field(default='local')
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: str | list[str] | None = None
    seed: int | None = None
    stream: bool | None = None


@app.on_event('startup')
async def wait_for_inference():
    for i in range(30):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f'{settings.inference_url}/v1/models')
                if r.status_code == 200:
                    logger.info('inference ready')
                    return
        except Exception:
            pass
        await asyncio.sleep(2)
    logger.warning('inference not ready after 60s')


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'api'}


@app.get('/health/ready')
async def health_ready() -> dict[str, Any]:
    """Checks connectivity to llama-server (inference). Uses OpenAI-compatible /v1/models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f'{settings.inference_url}/v1/models')
            if r.status_code == 200:
                return {'status': 'ready', 'inference': 'ok'}
            return {'status': 'degraded', 'inference_http': r.status_code}
    except Exception as e:
        logger.warning('inference health check failed: %s', e)
        return {'status': 'degraded', 'inference': str(e)}


@app.post('/v1/chat/completions')
@limiter.limit(f'{settings.rate_limit_per_minute}/minute')
async def chat_completions(
    request: Request,
) -> JSONResponse | StreamingResponse:
    request_id = request.state.request_id
    x_code_inference_intent = request.headers.get('X-code_inference-Intent')

    try:
        raw = await request.json()
        body = ChatCompletionRequest(**raw)
    except (ValidationError, ValueError, TypeError) as e:
        logger.warning('invalid request body request_id=%s error=%s', request_id, e)
        return JSONResponse(
            content={'error': 'invalid request body', 'detail': str(e)},
            status_code=422,
        )

    raw_messages = [m.model_dump() for m in body.messages]
    for m in raw_messages:
        m['content'] = extract_text(m.get('content'))

    pr = process_messages(
        raw_messages,
        max_chars=settings.max_prompt_chars,
        intent_header=x_code_inference_intent,
    )

    forward: dict[str, Any] = {
        'model': body.model,
        'messages': pr.messages,
    }
    for field in (
        'stream',
        'max_tokens',
        'temperature',
        'top_p',
        'frequency_penalty',
        'presence_penalty',
        'seed',
        'stop',
    ):
        val = getattr(body, field, None)
        if val is not None:
            forward[field] = val
    if body.model_extra:
        forward.update(body.model_extra)

    tools = body.model_extra.get('tools') if body.model_extra else None

    inf_url = f'{settings.inference_url}/v1/chat/completions'

    if body.stream:
        logger.info(
            'chat_completion streaming request_id=%s tags=%s truncated=%s pii_masked=%s',
            request_id,
            pr.tags,
            pr.truncated,
            pr.pii_masked,
        )
        return StreamingResponse(
            postprocess_streaming(_stream_chat(forward, inf_url), tools=tools),
            media_type='text/event-stream',
            headers={
                'X-Prompt-Truncated': '1' if pr.truncated else '0',
                'X-Prompt-Pii-Masked': '1' if pr.pii_masked else '0',
            },
        )

    inf = await _inference_request(forward, inf_url)

    logger.info(
        'chat_completion request_id=%s tags=%s truncated=%s pii_masked=%s inference_status=%s',
        request_id,
        pr.tags,
        pr.truncated,
        pr.pii_masked,
        inf.status_code,
    )

    try:
        payload = postprocess_nonstreaming(inf.json(), tools=tools)
    except Exception:
        payload = {'error': inf.text[:2000]}

    return JSONResponse(
        content=payload,
        status_code=inf.status_code,
        headers={
            'X-Prompt-Truncated': '1' if pr.truncated else '0',
            'X-Prompt-Pii-Masked': '1' if pr.pii_masked else '0',
        },
    )


@app.get('/')
async def web_ui():
    return FileResponse('app/static/index.html')


async def _stream_chat(forward: dict[str, Any], url: str):
    async with (
        httpx.AsyncClient(timeout=300.0) as client,
        client.stream('POST', url, json=forward) as resp,
    ):
        async for chunk in resp.aiter_bytes():
            yield chunk


async def _inference_request(
    forward: dict[str, Any],
    url: str,
    timeout: float = 300.0,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.post(url, json=forward)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_exc = e
            if attempt < 2:
                await asyncio.sleep(2**attempt)
    raise last_exc  # type: ignore[arg-type]
