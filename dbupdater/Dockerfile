FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV MYSQL_IP=127.0.0.1
ENV MYSQL_PORT=3306
ENV MYSQL_USER=EXAMPLE
ENV MYSQL_PASSWORD=EXAMPLE
ENV MYSQL_DB=EXAMPLE
ENV REDIS_IP=ldbredis
ENV REDIS_PORT=6379

RUN apt update && \
    apt upgrade -y && \
    apt install -y python3 \
	python3-simplejson \
	python3-dateutil \
	python3-redis \
    python3-mysql.connector \
	inotify-tools \
	python3-toml

ADD ./monitor_file-for-dbupdate.sh /usr/share/monitor_filesystem.sh
ADD ./*.py /usr/share/

VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_filesystem.sh
