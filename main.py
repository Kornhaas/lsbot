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
        if int(strftime("%M")) % 30 == 0 and int(strftime("%S") < 10):
            ls.login()

        accidents = ls.get_all_accidents()

        for key, accident in accidents.iteritems():
            if accident['status'] == 'rot' or accident['status'] == 'elb':
                if accident['name'] != '"Feuerprobealarm an Schule"':
                    ls.get_accident(key, accident)

        sleep(10)


if __name__ == "__main__":
    main()
