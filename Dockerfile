FROM alpine:3.9

RUN apk add --update \
    python3 python3-dev \
    py3-cryptography \
    && rm -rf /var/cache/apk/*

COPY ./requirements.txt /usr/local/tgbot/requirements.txt
RUN pip3 install -r /usr/local/tgbot/requirements.txt
COPY . /usr/local/tgbot
WORKDIR /usr/local/tgbot

ENTRYPOINT ["/usr/bin/env", "python3", "main.py"]
