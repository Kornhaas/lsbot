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

    while True:
        ls.generate_missions()

        accidents = ls.get_all_accidents()

        for acc in accidents:
            details = ls.get_accident_details(acc['id'])
            if not (details['vehicles']['at_mission'] or details['vehicles']['driving']):
                ls.send_car_to_accident(acc['id'], details['vehicles']['avalible'][0]['id'])
                print('send car to %s' % acc['caption'])

        sleep(30)


if __name__ == "__main__":
    main()
