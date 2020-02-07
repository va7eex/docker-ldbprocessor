#!/bin/bash

FILEPATH=/var/ldbinvoice

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXARNEWINVOICE_[0-9]+_[0-9]+\.[Xx][Ll][Ss] ]]; then
		echo 'found '$path$file
		in2csv $path$file > /tmp/"${file%.*}.csv"
		echo 'processing ARINVOICE'
		python3 /usr/share/process_arinvoice.py /tmp/"${file%.*}.csv" $path$(date +%Y-%h-%d)"_for-PO-import.txt" $path$(date +%Y-%h-%d)"_pricedeltareport.txt"
	fi
    done
