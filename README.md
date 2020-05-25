# docker-ldbprocessor

Tools to assist in receiving of inventory from the LDB Store 100 to Infospec's Profitek backend.

After cloning reposity run `createconstants.sh` wizard to populate ldb-compose.yaml and constants.py. Once the wizard is completed create all containers by running `docker-compose -f docker-ldbprocessor/ldb-compose.yaml up -d`.

The mounted volume in ldb-compose.yaml should be a SMB directory network accessible unless it is accessible from the computer docker is running on.

If running SMB: the user and/or group of each docker app must have read/write permissions in directory.

# LDBprocessor_bc

This image takes the output file from a Motorola CS3000 barcode scanner and formats them into a (mostly) human readable count of all barcodes scanned per shipment.

To make this work with other devices, a `barcodes.csv` file must be created with the headerless format: `%d/%m/%Y, %h:%M:%S, $barcodeType (unused), $barcode` per line, an example file would be:

```csv
$ cat barcodes.csv

32/13/1966, 13:50:53, 3, C1625575
32/13/1966, 13:50:53, 3, C1625579
32/13/1966, 13:50:54, 3, C1625581
32/13/1966, 13:50:55, 3, C1625582
32/13/1966, 13:50:55, 3, C1625576
32/13/1966, 14:01:46, 3, C1625569
32/13/1966, 14:01:48, 0F, 5918923820
32/13/1966, 14:01:49, 0B, 87614498136
32/13/1966, 14:01:49, 6, 2156843648
32/13/1966, 14:01:50, 6, 64864789
[...]
```

For future reference the unused field of `$barcodeType` is in reference to the hexadecimal values (just pretend the `0x` is prepended to everything in column 3) of Appendix Table B-1 on the [Zebra CS3000/3070 manual](https://www.zebra.com/content/dam/zebra_new_ia/en-us/manuals/barcode-scanners/cs3070-prg-en.pdf). While this information isn't particularly useful in the process of receiving inventory, it is kind of interesting that the majority of barcodes on a particular pallet are Interleaved 2 or 5.


# LDBprocessor_os


# LDBprocessor_ar
