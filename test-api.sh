curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model.gguf",
    "messages": [{"role": "user", "content": "Hi"}],
    "options": {
      "num_ctx": 1024,
      "num_gpu": 0
    }
  }'