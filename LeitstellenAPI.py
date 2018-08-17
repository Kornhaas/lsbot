# coding=utf-8
import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep


class LeitstellenAPI:
    session = None
    authenticity_token = ''
    user = {"name": "",
            "id": 0
            }

    headers = {
        "Content - Type": "application / x - www - form - urlencoded",
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }

    def __init__(self, email, password):
        with open('game_data.json') as d:
            self.data = json.load(d)
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
                self.user['name'] = user.text[1:]
                id = re.findall('var\W+user_id\W*=\W*(\d+)\W*;', login_page.text)[0]
                self.user['id'] = int(id)
                break
        print('successfully logged in as %s' % self.user['name'])

    def get_all_missions(self):
        r = self.session.get('https://www.leitstellenspiel.de/')
        missions_json = re.findall('missionMarkerAdd\((.*?)\);', r.text)
        missions = {}
        for m in missions_json:
            mission = json.loads(m.encode().decode('unicode-escape'))
            mission['id'] = str(mission['id'])
            mission['missing'] = self.parse_missing(mission['missing_text'])
            missions[mission['id']] = mission
        return missions

    def get_mission_details(self, missionid):
        mission = {'vehicles': {}}
        r = self.session.get('https://www.leitstellenspiel.de/missions/%s' % missionid)
        mission_page = BeautifulSoup(r.content, 'html.parser')

        mission['vehicles']['driving'] = mission_page.find('table', {'id': 'mission_vehicle_driving'}) is not None
        mission['vehicles']['at_mission'] = mission_page.find('table', {'id': 'mission_vehicle_at_mission'}) is not None

        mission['vehicles']['avalible'] = []
        vehicle_table = mission_page.find('table', {'id': 'vehicle_show_table_all'})
        if vehicle_table is not None:
            vehicle_rows = vehicle_table.find('tbody').find_all('tr')
            for tr in vehicle_rows:
                type_id = tr.find('td', {'vehicle_type_id': True}).get('vehicle_type_id')
                v = {'id': int(tr.get('id')[24:]),
                     'type_id': int(type_id),
                     'caption': tr.get('vehicle_caption'),
                     'details': tr.find('input').attrs
                     }
                mission['vehicles']['avalible'].append(v)
        return mission

    def send_cars_to_mission(self, missionid, car_ids):
        url = 'https://www.leitstellenspiel.de/missions/%s/alarm' % missionid

        # todo this should be done in a single request...
        for car in car_ids:
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

    def parse_missing(self, missing_text):
        if missing_text is None:
            return None
        vehicle_matches = re.findall('(?:[,:]) (\d+) ([^,()]*?)(?: \([^()]*\))?(?=,|$)', missing_text)
        result = []
        for m in vehicle_matches:
            vtype = self.lookup_vehicle_type_by_name(m[1])
            for i in range(int(m[0])):
                result.append(vtype)
        return result

    def lookup_vehicle_type_by_name(self, name):
        if name in self.data['vehicle_type_names']:
            return self.data['vehicle_type_names'][name]
        else:
            print('WARNING: unknown vehicle name: %s' % name)
            return 'unknown'

    def probe_need(self, missionid, avalible_cars):
        if len(avalible_cars) == 0:
            print("no car avalible for probing")
            return
        carid = avalible_cars[0]['id']
        self.send_cars_to_mission(missionid, [carid])
        sleep(2)
        self.recall_car_from_mission(carid)

    def recall_car_from_mission(self, carid):
        self.session.get('https://www.leitstellenspiel.de/vehicles/%s/backalarm?return=mission' % carid)

    def lookup_vehicle_type_ids(self, type):
        if type in self.data['vehicle_type_ids']:
            return self.data['vehicle_type_ids'][type]
        else:
            raise AttributeError('unknown vehicle type: %s' % type)
