#!/bin/bash

sudo mysql -e "CREATE USER slave IDENTIFIED WITH mysql_native_password BY 'Passwordslave1%'"
sudo mysql -e "GRANT REPLICATION SLAVE on *.* to 'slave'@'%'"
sudo mysql -e "SHOW GRANTS FOR slave"