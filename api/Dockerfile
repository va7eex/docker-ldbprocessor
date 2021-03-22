FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV FLASK_APP=api.py
ENV MYSQL_IP=127.0.0.1
ENV MYSQL_PORT=3306
ENV MYSQL_USER=EXAMPLE
ENV MYSQL_PASSWORD=EXAMPLE
ENV MYSQL_DB=EXAMPLE
ENV REDIS_IP=127.0.0.1
ENV REDIS_PORT=6379
ENV LABEL_MAKER=127.0.0.1

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
     && date

RUN apt update \
    && apt upgrade -y \
    && apt install -y \
        python3 \
        python3-pip

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY *.py ./

ENTRYPOINT python3 -u -m flask run --host=0.0.0.0