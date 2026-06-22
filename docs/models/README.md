# Model weights (GGUF)

Place a **Llama 3.2** (or compatible) **GGUF** checkpoint in the Docker **model_data** volume as the file name configured by `MODEL_FILENAME` (default: `model.gguf`).

## Where to get a `.gguf` file

Weights are **not** in this repository (large files; see `.gitignore`).

- **Hugging Face** is the usual place to download a **`.gguf`** build: search for the model family you want (e.g. Llama 3.2) and **GGUF**, open the model page, use the **Files** tab, and download a **`.gguf`** artifact. For gated Meta models you must **log in** and **accept the license** on that page before downloading.
- **Meta** is the **licensor** of Llama; official distribution for developers often goes **through Hugging Face** (e.g. under the `meta-llama` organization). Meta does not always ship a ready-made **`.gguf`** on a separate “Meta-only” download page — **GGUF** is produced for **llama.cpp** and is commonly published on HF by Meta or by reputable conversion/quantization repos.

## Verifying downloads (supply chain hygiene)

- **Prefer official or well-known publishers** on Hugging Face (e.g. `meta-llama` for Llama, or established GGUF mirrors with clear provenance and many downloads). Avoid unknown mirrors or “one-click” sites.
- **Download from the real model URL** on **`huggingface.co`** (browser or `huggingface-cli`), not untrusted pasted links.
- **Check the artifact**: you want a **`.gguf`** file of **roughly the size** described on the model card for that quantization (e.g. Q4). A “model” that is only a few kilobytes is not a real checkpoint.
- **Checksums**: if the publisher lists **SHA256**, verify after download (e.g. `shasum -a 256 your-model.gguf` on macOS) and compare.
- **Do not run** random scripts or installers bundled alongside weights unless you trust the publisher; for this stack you only need the **`.gguf`** in the volume.
- **Risk in context**: a `.gguf` is **data** consumed by `llama.cpp`, not a macOS app you execute by double-clicking. The usual risks are **wrong/broken files**, **phishing / fake download pages**, or **trusting the wrong repo** — the same hygiene as any large download from the internet.

## Meta `llama-model` CLI (Docker, no host install)

The **`llama-stack`** image (Compose **profile `tools`**) installs Meta’s **`llama-models`** CLI. It mounts the same **`model_data`** volume at **`/models`** read-write so downloads land next to what **inference** reads (read-only).

```bash
docker compose --profile tools build llama-stack
docker compose --profile tools run --rm llama-stack llama-model list
docker compose --profile tools run --rm -it llama-stack llama-model download --source meta --model-id <MODEL_ID>
```

Use **`-it`** for `download` when the CLI prompts for a signed URL or other input.

Use the **signed URL** from Meta when prompted. Outputs are usually **not** GGUF; convert or add a **`.gguf`** for `llama.cpp` as described above.

## Example: copy into the volume

After the stack has been created once:

```bash
docker run --rm -v code-inference-ai_model_data:/models -v "$PWD:/host" alpine \
  cp /host/your-model.gguf /models/model.gguf
```

(Adjust the volume name prefix if your project directory name differs; use `docker volume ls` to find it.)

The **inference** service mounts `/models` read-only and passes `-m /models/model.gguf` to `llama-server` by default.

Do **not** commit `.gguf` files to git (see `.gitignore`).

To quickly restart the stack, run the following script:

```bash
./restart.sh
```

To download a model that works, run the following command:

```bash
curl -L "https://huggingface.co/unsloth/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf" -o ./models/Meta-Llama-3-1B-Instruct-Q4_K_M.gguf
```

curl -L https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf -o ./models/qwen2.5-coder-3b-instruct-q4_k_m.gguf

## Tool calling and model size

Small local models (≤3B parameters) **hallucinate tool calls** — they output `{"name":"read_file","arguments":{}}` even for simple chat like "hello" when tool definitions are present. This is a known limitation of small models, not a configuration issue.

| Model size | Tool calling reliability | Recommended for |
|------------|------------------------|----------------|
| 1B–3B | 🟡 Unreliable, hallucinates often | Chat-only, no tools needed |
| 7B | 🟢 Good with occasional misses | Light tool use, dev work |
| 14B+ | 🟢 Reliable | Production tool calling |

### Architecture: how tools flow

```
opencode CLI                    API                          llama.cpp
  │                             │                             │
  │ POST with tools=[…]         │                             │
  │────────────────────────────►│                             │
  │                             │────────────────────────────►│  --tools all
  │                             │   forwards tools + messages │  processes tools
  │                             │                             │  via Jinja template
  │◄────────────────────────────│◄────────────────────────────│
  │   tool_calls (converted)    │   raw JSON in content       │
  │                             │   post-processor converts   │
```

- **opencode CLI** sends `tools` in requests → `--tools all` enables llama.cpp to process them → the model outputs tool call JSON → the API post-processor converts raw JSON to OpenAI `tool_calls` format
- **Web UI** does **not** send `tools` → the model sees no tool definitions → responds naturally without hallucination

The web UI intentionally omits `tools` from requests because small models hallucinate tool calls when they see tool definitions, and web UI cannot execute filesystem tools anyway.

### Backend portability

The `--tools all` flag is **llama.cpp-specific**. If swapping to ollama or vLLM:
- Remove `--tools all` from the inference service command
- The API's `postprocessing.py` handles tool call conversion uniformly regardless of backend
- The API's `prompt.py` would need tool-injection logic if the new backend doesn't process `tools` natively

See `docs/settings.md` for the full post-processing reference.