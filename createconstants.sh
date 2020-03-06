echo "What is my mysql IP? (IP or name of container) [LDBdatabase]"

read myip

if [[ -z "$myip" ]]; then
    myip = "LDBdatabase"

echo "What is my mysql port? [3306]"

read myport

if [[ -z "$myport" ]]; then
    myport = "3306"

echo "What is my redis IP? (IP or name of container) [LDBredis]"

read myredis

if [[ -z "$myredis" ]]; then
    myredis = "LDBredis"

echo "What is my redis port? [6379]"

read myredisport

if [[ -z "$myredisport" ]]; then
    myredisport = "6379"

echo "What is the name of the database? (one word) [LDB]"

read mydb

if [[ -z "$mydb" ]]; then
    mydb = "LDB"

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
