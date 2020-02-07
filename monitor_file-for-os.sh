#!/bin/bash

FILEPATH=/var/ordersubmission

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXOMWOSRPDF_[0-9]+_[0-9]+\.[Xx][Ll][Ss] ]]; then
		echo 'found '$file
		in2csv $path$file > /tmp/"${file%.*}.csv"
		echo 'processing OSRPDF'
		cp /tmp/"${file%.*}.csv" /var/ldbinvoice/"${file%.*}.csv"
		python3 /usr/share/process_ordersubmission.py /tmp/"${file%.*}.csv" #>> $path$(date +%Y-%h-%d)"_log_ordersubmission.txt"
	fi
    done
