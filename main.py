#!/usr/bin/python
# -*- coding: utf-8 -*-

from time import *
from thread import start_new_thread
import sys

from LeitstellenAPI import LeitstellenAPI

class DevNull:
    def write(self, msg):
        pass


class Main:
    def __init__(self):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        sys.stderr = DevNull()
        email = raw_input('Email: ')
        password = raw_input('Passwort: ')

        self.ls = LeitstellenAPI(email, password)
        self.ls.login()

        while True:
            start_new_thread(self.thread, ())

            if int(strftime("%M")) % 30 == 0 and int(strftime("%S") < 10):
                self.ls.login()

            sleep(10)

    def thread(self):
        self.ls.get_all_accidents()

        for key, accident in self.accidents.iteritems():
            if accident['status'] == 'rot' or accident['status'] == 'elb':
                if accident['name'] != '"Feuerprobealarm an Schule"':
                    self.ls.get_accident(key, accident)


if __name__ == "__main__":
    main = Main()
