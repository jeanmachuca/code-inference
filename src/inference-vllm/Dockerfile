FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3 python3-pip curl
RUN pip install vllm --break-system-packages

WORKDIR /models
VOLUME ["/models"]

ENTRYPOINT []
CMD ["vllm", "serve", "Qwen/Qwen3-Coder-Next"]