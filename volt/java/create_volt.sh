#!/bin/sh


voltdb compile -o voltdns.jar  dns.sql
voltdb create catalog voltdns.jar
