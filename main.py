#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
from time import *
import os.path
from LeitstellenAPI import LeitstellenAPI


def main():
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
        ls.generate_missions()

        missions = ls.get_all_missions()
        for key, m in missions.items():
            if key not in last_missions:
                print('new mission: %s' % m['caption'])
        for key, m in last_missions.items():
            if key not in missions:
                print('finished mission: %s' % m['caption'])
        last_missions = missions

        for id, m in missions.items():
            details = ls.get_mission_details(id)
            if not details['vehicles']['driving']:
                if not details['vehicles']['at_mission'] and m['missing'] is None:
                    # no stated need and no vehicles at mission: probe need
                    print('probe need for: %s' % m['caption'])
                    ls.probe_need(id, details['vehicles']['avalible'])
                if m['missing'] is not None:
                    avalible_cars = details['vehicles']['avalible']
                    need_help = False
                    car_ids = []
                    for misisng_type in m['missing']:
                        type_ids = ls.lookup_vehicle_type_ids(misisng_type)
                        found_car = False
                        for car in avalible_cars:
                            if car['type_id'] in type_ids:
                                car_ids.append(car['id'])
                                avalible_cars.remove(car)
                                found_car = True
                                break
                        if not found_car:
                            need_help = True
                    if need_help:
                        # todo open mission for verband
                        pass
                    ls.send_cars_to_mission(id, car_ids)
                    print('sent cars to mission: %s' % m['caption'])

        sleep(30)


if __name__ == "__main__":
    main()
