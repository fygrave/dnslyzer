#!/bin/sh

celery worker -I indexdns -E -c 40
