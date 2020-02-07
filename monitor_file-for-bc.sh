#!/bin/bash

FILEPATH=/var/ldbinvoice

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
	if [[ $file =~ barcodes\.csv ]]; then
		python3 /usr/share/process_barcodes.py $path$file $path$(date +%Y-%h-%d)"_scanlog.txt" #>> $path$(date +%Y%m%d)"_log_barcodes.txt"
	fi
    done
