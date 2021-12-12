#!/bin/bash

sudo mysql -e "create database sbtest"
sudo mysql -e "create user sbtest_user identified by 'Passwordslave1%'"
sudo mysql -e "grant all on sbtest.* to 'sbtest_user'@'%'"
sudo mysql -e "show grants for sbtest_user"

sysbench \
--db-driver=mysql \
--mysql-user=sbtest_user \
--mysql_password=password \
--mysql-db=sbtest \
--mysql-port=3306 \
--tables=16 \
--table-size=10000 \
/usr/share/sysbench/oltp_read_write.lua prepare

sysbench \
--db-driver=mysql \
--mysql-user=sbtest_user \
--mysql_password=password \
--mysql-db=sbtest \
--mysql-port=3306 \
--tables=16 \
--table-size=10000 \
--threads=8 \
--time=300 \
--events=0 \
--report-interval=1 \
/usr/share/sysbench/oltp_read_write.lua run