FROM ubuntu

RUN apt-get update && apt-get install -y curl zstd && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /models
VOLUME ["/models"]

ENTRYPOINT []
CMD ["ollama", "--help"]