#!/bin/bash
#title           :monitor_file-for-ar.sh
#description     :Monitors a directory for appearance of .xls files matching regex
#author		 :David Rickett
#date            :2020
#usage		 :bash monitor_file-for-ar.sh
#notes           :Invoked by Docker Entrypoint command
#bash_version    :Ubuntu LTS
#==============================================================================

FILEPATH=/var/ldbinvoice

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXARNEWINVOICE_[0-9]+_[0-9]+\.[Xx][Ll][Ss]$ ]]; then
			echo 'found '$path$file
			mv $path$file $path$file.bak
			in2csv --format xls $path$file.bak > /tmp/"${file%.*}.csv"
			echo 'processing ARINVOICE'
			python3 /usr/share/process_arinvoice.py \
				/tmp/"${file%.*}.csv"

	fi
    done
