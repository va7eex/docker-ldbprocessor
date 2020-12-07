#!/bin/bash
#title           :monitor_file-for-os.sh
#description     :Monitors a directory for appearance of .xls files matching regex
#author          :David Rickett
#date            :2020
#usage           :bash monitor_file-for-os.sh
#notes           :Invoked by Docker Entrypoint command
#bash_version    :Ubuntu LTS
#==============================================================================

FILEPATH=/var/ldbinvoice
IMPORTPATH=/var/import

inotifywait -m $IMPORTPATH -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXOMWOSRPDF_[0-9]+_[0-9]+\.[Xx][Ll][Ss] ]]; then
		echo 'found '$file
		html2csv $path$file -o /tmp/"${file%.*}.csv"
		echo 'processing OSRPDF'
#		cp /tmp/"${file%.*}.csv" /var/ldbinvoice/"${file%.*}.csv"
		python3 -u /usr/share/process_ordersubmission.py \
			/tmp/"${file%.*}.csv" \
			/var/ldbinvoice \
			MYSQL_IP=$MYSQL_IP \
                        MYSQL_PORT=$MYSQL_PORT \
                        MYSQL_USER=$MYSQL_USER \
                        MYSQL_PASS=$MYSQL_PASSWORD \
                        MYSQL_DB=$MYSQL_DATABASE \
                        REDIS_IP=$REDIS_IP \
                        REDIS_PORT=$REDIS_PORT
	fi
    done
