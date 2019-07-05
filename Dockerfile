FROM alpine:3.9

RUN apk add --update \
    python3 python3-dev \
    py3-cryptography \
    && rm -rf /var/cache/apk/*

COPY . /usr/local/tgbot
WORKDIR /usr/local/tgbot
RUN pip3 install -r /usr/local/tgbot/requirements.txt

ENTRYPOINT ["/usr/bin/env", "python3", "main.py"]
