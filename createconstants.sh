echo "What is my mysql IP? (IP or name of container)"

read myip

echo "What is my mysql port?"

read myport

echo "What is my redis IP? (IP or name of container)"

read myredis

echo "What is my redis port? (default 6379)"

read myredisport

echo "What is the name of the database? (one word)"

read mydb

echo "Who will be the user? (one word)"

read myname

echo "What will be the user password? (this will be stored in plain text)"

read mypass

echo "Finally, what will be the root password? (this will be stored in plain text)"

read rootpw

echo "MYSQL_IP='${myip}'" > ./constants.py
echo "MYSQL_PORT='${myport}'" >> ./constants.py
echo "MYSQL_DATABASE='${mydb}'" >> ./constants.py
echo "MYSQL_USER='${myname}'" >> ./constants.py
echo "MYSQL_PASS='${mypass}'" >> ./constants.py

sed -i "s#replacerootpwd#${rootpw}#g" ./ldb-compose.yaml
sed -i "s#replacedb#${mydb}#g" ./ldb-compose.yaml
sed -i "s#replaceuser#${myname}#g" ./ldb-compose.yaml
sed -i "s#replacepwd#${mypass}#g" ./ldb-compose.yaml
