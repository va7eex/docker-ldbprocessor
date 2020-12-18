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

RUN echo hello

RUN apt update
RUN apt upgrade -y
RUN apt install -y python3 \
#	python3-mysqldb \
	python3-simplejson \
	python3-dateutil \
	python3-mysql.connector \
	python3-redis \
	python3-pip \
	inotify-tools

RUN pip3 install html-to-csv \
	csvkit

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN date

ADD ./monitor_file-for-os.sh /usr/share/monitor_filesystem.sh
ADD ./*.py /usr/share/

VOLUME ["/var/import"]
VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_filesystem.sh
