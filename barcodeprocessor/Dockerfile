FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV APIURL=127.0.0.1
ENV APIKEY=''

RUN apt update && \
    apt upgrade -y &&\
    apt install -y python3 \
	python3-simplejson \
	python3-dateutil \
	python3-pip \
	inotify-tools

RUN pip3 install urllib3

ADD ./monitor_file-for-bc.sh /usr/share/monitor_filesystem.sh
ADD ./*.py /usr/share/

VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_filesystem.sh
