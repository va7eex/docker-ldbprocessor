FROM ubuntu:20.04

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV IMAP_ADDR=EXAMPLE \
    IMAP_USER=EXAMPLE \
    IMAP_PASS=EXAMPLE \
    IMAP_PORT=EXAMPLE

RUN apt update \
    && apt upgrade -y \
    && apt install -y python3 \
	python3-email
#	python3-mysqldb \
	python3-simplejson \
	python3-dateutil \
	python3-mysql.connector \
	python3-redis \
	python3-pip \


RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && date

ADD ./mail-attachments-archiver/ /usr/share/
ADD ./mail-sync.py /usr/share/

VOLUME ["/var/import"]
VOLUME ["/var/ldbinvoice"]

ENTRYPOINT python3 /usr/share/mail-sync.py
