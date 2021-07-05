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

sleep 6m

inotifywait -m $IMPORTPATH -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXOMWOSRPDF_[0-9]+_[0-9]+\.[XxLlSs]{3,4}$ ]]; then
		echo 'found '$file
		html2csv $path$file -o /tmp/"${file%.*}.csv"
		echo 'processing OSRPDF'
#		cp /tmp/"${file%.*}.csv" /var/ldbinvoice/"${file%.*}.csv"
		python3 -u /usr/share/process_ordersubmission.py \
			/tmp/"${file%.*}.csv"
	fi
    done
