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
        # temp hack: filter out verband-missions so that resources dont get stuck on unmanagable big missions
        # also filter 'sw' missions (with a timer, because they also take up vehicles for to much time)
        # todo better filter criteria
        for k in list(missions):
            if missions[k]['user_id'] != ls.user['id'] or missions[k]['sw']:
                del missions[k]

        for key, m in missions.items():
            if key not in last_missions:
                print('new mission: %s' % m['caption'])
        for key, m in last_missions.items():
            if key not in missions:
                print('finished mission: %s' % m['caption'])
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
                        print('sent cars to mission: %s' % m['caption'])
                elif not details['vehicles']['at_mission']:
                    # no stated need and no vehicles at mission: probe need
                    print('probe need for: %s' % m['caption'])
                    ls.probe_need(id, details['vehicles']['avalible'])

        sleep(30)


if __name__ == "__main__":
    main()
