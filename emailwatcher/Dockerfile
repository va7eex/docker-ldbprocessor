FROM ubuntu:latest

LABEL maintainer="David Rickett"

ARG TZ=America/Vancouver
ARG DEBIAN_FRONTEND=noninteractive

ENV IMAP_ADDR=EXAMPLE
ENV IMAP_USER=EXAMPLE
ENV IMAP_PASS=EXAMPLE
ENV IMAP_PORT=EXAMPLE
ENV SYNCTIME=1

RUN apt update \
    && apt upgrade -y \
    && apt install -y python3 \
    python3-pip \
    wget

RUN pip3 install schedule \
    argparse

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && date

#RUN echo hello
COPY mail-attachments-archiver /usr/share/
COPY sync-mail.py /usr/share/
COPY config.json /usr/share/

VOLUME ["/var/import"]
VOLUME ["/var/ldbinvoice"]

#sleep initially so the rest of the containers can set themselves up.
ENTRYPOINT sleep 6m && python3 -u /usr/share/sync-mail.py
