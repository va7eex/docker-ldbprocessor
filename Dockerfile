FROM ubuntu:18.04

LABEL maintainer="David Rickett"

ARG DEBIAN_FRONTEND=noninteractive

ARG MYSQL_ADDRESS=127.0.0.1
ARG MYSQL_PORT=3306
ARG MYSQL_DB="example"
ARG MYSQL_USER="example"
ARG MYSQL_PASSWORD="example"

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

#RUN sed -i s#mysql-ip#$MYSQL_ADDRESS#g /usr/share/constants.py
#RUN sed -i s#mysql-port#$MYSQL_PORT#g /usr/share/constants.py
#RUN sed -i s#mysql-database#$MYSQL_DB#g /usr/share/constants.py
#RUN sed -i s#mysql-user#$MYSQL_USER#g /usr/share/constants.py
#RUN sed -i s#mysql-pass#$MYSQL_PASSWORD#g /usr/share/constants.py

VOLUME ["/var/ldbinvoice"]

ENTRYPOINT bash /usr/share/monitor_ldbinvoice.sh
