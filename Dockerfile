FROM alpine:latest

RUN apk --update --no-cache add \
    docker-cli \
    docker-cli-compose

COPY . /repo
WORKDIR /repo

VOLUME /workspace

ENTRYPOINT ["/repo/start.sh"]
