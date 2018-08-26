#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import sys
from time import *
import os.path
from LeitstellenAPI import LeitstellenAPI
import logging
import sqlite3


class AbstractPeriodicFunction:
    def __init__(self):
        raise NotImplementedError()

    def get_name(self):
        raise NotImplementedError()

    def get_wait_time(self):
        raise NotImplementedError()

    def run(self, ls):
        raise NotImplementedError()


class CrewHirer(AbstractPeriodicFunction):
    def __init__(self):
        pass

    def get_name(self):
        return 'CREW_HIRE'

    def get_wait_time(self):
        return 24*60*60

    def run(self, ls):
        logging.info('hire crew in every building')
        all_buildings = ls.get_all_buildings()
        for id, b in all_buildings.items():
            if b['user_id'] == ls.user['id'] and b['personal_count'] > 0:
                ls.hire_crew(id, 3)


periodic_functions = [CrewHirer()]


def main():
    # connect the db
    db = sqlite3.connect('lsbot.db')
    # create all missing db tables
    c = db.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS periodic_tasks (id INTEGER PRIMARY KEY, name TEXT UNIQUE, last_run INTEGER);')
    db.commit()

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

    last_missions = {}
    while True:
        logging.info('checking periodic tasks')
        for func in periodic_functions:
            c.execute('SELECT last_run FROM periodic_tasks WHERE name=?', (func.get_name(),))
            last_run = c.fetchone()
            if last_run is None or last_run[0] + func.get_wait_time() < time():
                logging.info('running periodic task "%s"' % func.get_name())
                func.run(ls)
                c.execute('INSERT OR REPLACE INTO periodic_tasks(name, last_run) VALUES(?, ?)', (func.get_name(), time()))
                db.commit()

        ls.generate_missions()

        missions = ls.get_all_missions()
        # temp hack: filter out verband-missions so that resources dont get stuck on unmanagable big missions
        # also filter 'sw' missions (with a timer, because they also take up vehicles for to much time)
        # todo better filter criteria
        for k in list(missions):
            if missions[k]['user_id'] != ls.user['id'] or missions[k]['sw']:
                del missions[k]

        for key, m in missions.items():
            if key not in last_missions:
                logging.info('new mission: %s' % m['caption'])
        for key, m in last_missions.items():
            if key not in missions:
                logging.info('finished mission: %s' % m['caption'])
        last_missions = missions

        for id, m in missions.items():
            details = ls.get_mission_details(id)
            if not details['vehicles']['driving']:  # only work with missions with no cars currently driving to them
                if m['missing'] is not None:
                    avalible_cars = details['vehicles']['avalible']
                    need_help = False
                    car_ids = []
                    for missing_type in m['missing']:
                        type_ids = ls.lookup_vehicle_type_ids(missing_type)
                        found_car = False
                        for car in avalible_cars:
                            if car['type_id'] in type_ids:
                                car_ids.append(car['id'])
                                avalible_cars.remove(car)
                                found_car = True
                                break
                        if not found_car:
                            need_help = True
                    # todo deal with missing crew
                    if need_help:
                        # todo open mission for verband
                        pass
                    if len(car_ids) > 0:
                        ls.send_cars_to_mission(id, car_ids)
                        logging.info('sent cars to mission: %s' % m['caption'])
                        sleep(2)
                elif not details['vehicles']['at_mission']:
                    # no stated need and no vehicles at mission: probe need
                    logging.info('probe need for: %s' % m['caption'])
                    ls.probe_need(id, details['vehicles']['avalible'])
                    sleep(2)

        sleep(30)


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
