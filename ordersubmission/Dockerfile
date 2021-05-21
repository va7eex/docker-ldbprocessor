FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV APIURL=127.0.0.1
ENV APIKEY=''

RUN apt update && \
    apt upgrade -y && \
    apt install -y python3 \
    python3-simplejson \
    python3-dateutil \
    python3-redis \
    python3-pip \
    inotify-tools \
    csvkit

RUN pip3 install html-to-csv urllib3

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && date

ADD ./monitor_file-for-os.sh /usr/share/monitor_filesystem.sh
ADD ./*.py /usr/share/

VOLUME ["/var/import"]
VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_filesystem.sh
