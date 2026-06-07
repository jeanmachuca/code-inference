FROM alpine:latest

RUN apk --update --no-cache add \
    docker-cli \
    docker-cli-compose

WORKDIR /workspace
COPY . .
VOLUME /workspace

ENTRYPOINT ["/workspace/start.sh"]
