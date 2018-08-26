#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import sys
from time import *
import os.path
from typing import List
from tasks import *


def main():
    db = DBWrapper('lsbot.db')

    config = {}
    if os.path.isfile('config.json'):
        with open('config.json') as cf:
            config = json.load(cf)

    if 'email' not in config:
        config['email'] = raw_input('Email: ')
    if 'password' not in config:
        config['password'] = raw_input('Passwort: ')

    ls = LeitstellenAPI(config['email'], config['password'])
    ls.login()

    periodic_tasks: List[AbstractPeriodicTask] = [CrewHirer(),
                                                  MissionGenerator(),
                                                  MissionController(),
                                                  ]

    while True:
        for func in periodic_tasks:
            last_run = db.get_task_last_run(func.get_name())
            if last_run is None or last_run + func.get_wait_time() < time():
                logging.debug('running periodic task "%s"' % func.get_name())
                func.run(ls, db)
                db.write_task_last_run(func.get_name(), time())


def setup_logger(debug=False):
    class StdOutFilter(logging.Filter):
        def filter(self, rec):
            return rec.levelno <= logging.INFO

    logging.getLogger("").setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(levelname)s [%(asctime)s] %(message)s')

    sout_handler = logging.StreamHandler(sys.stdout)
    sout_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    sout_handler.setFormatter(formatter)
    sout_handler.addFilter(StdOutFilter())

    serr_handler = logging.StreamHandler(sys.stderr)
    serr_handler.setLevel(logging.WARN)
    serr_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('lsbot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logging.getLogger("").addHandler(sout_handler)
    logging.getLogger("").addHandler(serr_handler)
    logging.getLogger("").addHandler(file_handler)


if __name__ == "__main__":
    setup_logger(debug=True)
    main()
