#!/usr/bin/python
# -*- coding: utf-8 -*-

from time import *

from LeitstellenAPI import LeitstellenAPI


def main():
    email = raw_input('Email: ')
    password = raw_input('Passwort: ')

    ls = LeitstellenAPI(email, password)
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
