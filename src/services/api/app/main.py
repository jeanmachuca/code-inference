from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.prompt import process_messages

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title='code_inference AI API', version='0.1.0')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default='local')
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None


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
    body: ChatCompletionRequest,
    x_code_inference_intent: str | None = Header(default=None, alias='X-code_inference-Intent'),
) -> JSONResponse:
    request_id = str(uuid.uuid4())
    raw_messages = [m.model_dump() for m in body.messages]

    pr = process_messages(
        raw_messages,
        max_chars=settings.max_prompt_chars,
        intent_header=x_code_inference_intent,
    )

    forward: dict[str, Any] = {
        'model': body.model,
        'messages': pr.messages,
    }
    if body.max_tokens is not None:
        forward['max_tokens'] = body.max_tokens
    if body.temperature is not None:
        forward['temperature'] = body.temperature

    async with httpx.AsyncClient(timeout=300.0) as client:
        inf = await client.post(
            f'{settings.inference_url}/v1/chat/completions',
            json=forward,
            headers={'Content-Type': 'application/json'},
        )

    # Log metadata only (no raw prompts) — see docs/requirements.md
    logger.info(
        'chat_completion request_id=%s tags=%s truncated=%s pii_masked=%s inference_status=%s',
        request_id,
        pr.tags,
        pr.truncated,
        pr.pii_masked,
        inf.status_code,
    )

    try:
        payload = inf.json()
    except Exception:
        payload = {'error': inf.text[:2000]}

    return JSONResponse(
        content=payload,
        status_code=inf.status_code,
        headers={
            'X-Request-Id': request_id,
            'X-Prompt-Truncated': '1' if pr.truncated else '0',
            'X-Prompt-Pii-Masked': '1' if pr.pii_masked else '0',
        },
    )
