#!/bin/bash
#title           :monitor_file-for-bc-redis.sh
#description     :Monitors a directory for appearance of a file called barcodes.csv, uses redis databases
#author          :David Rickett
#date            :2020
#usage           :bash monitor_file-for-bc-redis.sh
#notes           :Invoked by Docker Entrypoint command
#bash_version    :Ubuntu LTS
#==============================================================================

FILEPATH=/var/ldbinvoice

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
	if [[ $file =~ barcodes\.csv$ ]]; then
        echo "The file '$file' appeared in directory '$path' via '$action'"
		mv $path$file $path$file.lock
		python3 /usr/share/process_barcodes.py $path$file.lock \
			$path$(date +%Y-%h-%d)"_scanlog.txt"

#		cp $path"processedbarcodes.json"
	fi
    done
