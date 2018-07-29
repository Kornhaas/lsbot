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
            if not (details['vehicles']['at_mission'] or details['vehicles']['driving']):
                ls.send_car_to_mission(id, details['vehicles']['avalible'][0]['id'])
                print('send car to %s' % m['caption'])

        sleep(30)


if __name__ == "__main__":
    main()
