# coding=utf-8

import requests
from bs4 import BeautifulSoup
import re
import json


class LeitstellenAPI:
    session = None
    authenticity_token = ''
    username = ''

    headers = {
        "Content - Type": "application / x - www - form - urlencoded",
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def login(self):
        self.session = requests.session()
        self.session.headers.update(self.headers)

        for i in range(1, 5):
            print('logging in... [try %d]' % i)
            data = {
                'authenticity_token': self.authenticity_token,
                'user[email]': self.email,
                'user[password]': self.password,
                'user[remember_me]': 1,
                'commit': 'Einloggen'
            }
            r = self.session.post("https://www.leitstellenspiel.de/users/sign_in", data=data)

            login_page = BeautifulSoup(r.content, 'html.parser')
            self.authenticity_token = login_page.find('input', {'name': 'authenticity_token'}).get('value')

            user = login_page.find('a', {'id': 'navbar_profile_link'})
            if user:
                self.username = user.text[1:]
                break
        print('successfully logged in as %s' % self.username)

    def get_all_missions(self):
        r = self.session.get('https://www.leitstellenspiel.de/')
        missions_json = re.findall('missionMarkerAdd\((.*?)\);', r.text)
        missions = {}
        for m in missions_json:
            mission = json.loads(m.encode().decode('unicode-escape'))
            mission['id'] = str(mission['id'])
            missions[mission['id']] = mission
        # todo process the missing_text
        return missions

    def get_mission_details(self, missionid):
        mission = {'vehicles': {}}
        r = self.session.get('https://www.leitstellenspiel.de/missions/%s' % missionid)
        mission_page = BeautifulSoup(r.content, 'html.parser')

        mission['vehicles']['driving'] = mission_page.find('table', {'id': 'mission_vehicle_driving'}) is not None
        mission['vehicles']['at_mission'] = mission_page.find('table', {'id': 'mission_vehicle_at_mission'}) is not None

        vehicle_rows = mission_page.find('table', {'id': 'vehicle_show_table_all'}).find('tbody').find_all('tr')
        mission['vehicles']['avalible'] = []
        for tr in vehicle_rows:
            v = {'id': int(tr.get('id')[24:]),
                 'type': tr.get('vehicle_type'),
                 'caption': tr.get('vehicle_caption'),
                 'details': tr.find('input').attrs
                 }
            mission['vehicles']['avalible'].append(v)
        return mission

    def send_car_to_mission(self, missionid, car):
        url = 'https://www.leitstellenspiel.de/missions/%s/alarm' % missionid
        data = {
            'authenticity_token': self.authenticity_token,
            'commit': 'Alarmieren',
            'next_mission': 0,
            'vehicle_ids[]': car
        }

        self.session.post(url, data=data)

    def generate_missions(self):
        url = 'https://www.leitstellenspiel.de/mission-generate'
        try:
            self.session.get(url, headers={"X-CSRF-Token": self.authenticity_token, "User-Agent": self.headers["User-Agent"]})
        except Exception as e:
            print('error reloading missions')
            print(e)
