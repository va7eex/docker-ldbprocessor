FROM ubuntu:18.04

LABEL maintainer="David Rickett"

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt upgrade -y
RUN apt install -y python3 \
	python3-mysqldb \
	python3-simplejson \
	python3-dateutil \
	python3-mysql.connector \
	inotify-tools \
	csvkit


ADD ./monitor_ldbinvoice.sh /usr/share/
ADD ./constants.py /usr/share/
ADD ./process_arinvoice.py /usr/share/
ADD ./process_ordersubmission.py /usr/share/
ADD ./process_barcodes.py /usr/share/

VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_ldbinvoice.sh
