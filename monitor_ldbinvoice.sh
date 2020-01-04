#!/bin/bash

FILEPATH=/var/ldbinvoice

inotifywait -m $FILEPATH -e close_write -e moved_to |
    while read path action file; do
        echo "The file '$file' appeared in directory '$path' via '$action'"
        if [[ $file =~ XXARNEWINVOICE_[0-9]+_[0-9]+\.[Xx][Ll][Ss] ]]; then
#        if [ "xls" = "${file##*.}" ]; then
		echo 'found '$path$file
		in2csv $path$file > /tmp/"${file%.*}.csv"
		echo 'processing ARINVOICE'
		python3 /usr/share/process_arinvoice.py /tmp/"${file%.*}.csv" $path$(date +%Y%m%d)"_for-PO-import-test.txt" $path$(date +%Y%m%d)"_pricedeltareport-test.txt"
		#python3 ~/processcsv.py /tmp/"${file%.*}.csv" > ~/ldbinvoice/$(date +%Y-%B-%d)_orderinvoice.txt
		#python3 ~/spotcheck.py /tmp/"${file%.*}.csv" > ~/ldbinvoice/$(date +%Y-%B-%d)_spotcheck.txt
		#rm ~/ldbinvoice/$file
		#rm /tmp/"${file%.*}.csv"
        elif [[ $file =~ XXOMWOSRPDF_[0-9]+_[0-9]+\.[Xx][Ll][Ss] ]]; then
		echo 'found '$file
		in2csv $path$file > /tmp/"${file%.*}.csv"
		echo 'processing OSRPDF'
		python3 /usr/share/process_ordersubmission.py /tmp/"${file%.*}.csv" #>> $path$(date +%Y%m%d)"_log_ordersubmission.txt"
	elif [[ $file =~ barcodes\.csv ]]; then
		python3 /usr/share/process_barcodes.py $path$file $path$(date +%Y%m%d)"_scanlog-test.txt" #>> $path$(date +%Y%m%d)"_log_barcodes.txt"
	fi
    done
