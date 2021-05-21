FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV APIURL=127.0.0.1
ENV APIKEY=''
ENV PRICECHANGEIGNORE=0.00

RUN apt update && \
    apt upgrade -y && \
    apt install -y python3 \
    python3-pip \
    python3-simplejson \
    python3-dateutil \
    python3-redis \
    inotify-tools \
    csvkit

RUN pip3 install urllib3

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
     && date

ADD ./monitor_file-for-ar.sh /usr/share/monitor_filesystem.sh
ADD ../api/LineItem.py /usr/share/
ADD ./*.py /usr/share/

VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_filesystem.sh
