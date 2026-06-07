FROM alpine:latest

RUN apk --update --no-cache add \
    docker-cli \
    docker-cli-compose

COPY . /workspace
WORKDIR /workspace
VOLUME /workspace

ENTRYPOINT ["start.sh"]
