#!/usr/bin/env python

from celery import Celery
import logging

celery = Celery('tasks', broker='amqp://guest@localhost//')

@celery.task
def dnspack(pack):
    logger = logging.getLogger()
    logger.info("got dnspack")

