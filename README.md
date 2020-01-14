# docker-ldbprocessor

Tools to assist in receiving of inventory from the LDB Store 100 to Infospec's Profitek backend.

After cloning reposity run `createconstants.sh` wizard to populate ldb-compose.yaml and constants.py. Once the wizard is completed create all containers by running `docker-compose -f docker-ldbprocessor/ldb-compose.yaml up -d`.

The mounted volume in ldb-compose.yaml should be a SMB directory network accessible unless it is accessible from the computer docker is running on.

If running SMB: the user and/or group of each docker app must have read/write permissions in directory.
