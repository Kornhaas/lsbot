# coding=utf-8
import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep
import logging


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
        with open('game_data.json', encoding='utf-8') as d:
            self.data = json.load(d)
        self.email = email
        self.password = password

    def login(self):
        self.session = requests.session()
        self.session.headers.update(self.headers)

        for i in range(1, 5):
            logging.info('logging in... [try %d]' % i)
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
        logging.info('successfully logged in as %s' % self.user['name'])

    def get_all_missions(self):
        r = self.session.get('https://www.leitstellenspiel.de/')
        missions_json = re.findall('missionMarkerAdd\((.*?)\);', r.text)
        missions = {}
        for m in missions_json:
            mission = json.loads(m)
            mission['id'] = str(mission['id'])
            missions[mission['id']] = mission
        return missions

    def get_all_buildings(self):
        r = self.session.get('https://www.leitstellenspiel.de/')
        buildings_json = re.findall('buildingMarkerAdd\((.*?)\);', r.text)
        buildings = {}
        for b in buildings_json:
            building = json.loads(b)
            building['id'] = str(building['id'])
            buildings[building['id']] = building
        return buildings

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
        logging.info('https://www.leitstellenspiel.de/missions/%s/alarm' % missionid)

        url = 'https://www.leitstellenspiel.de/missions/%s/alarm' % missionid

        data = {
            'authenticity_token': self.authenticity_token,
            'commit': 'Alarmieren',
            'next_mission': 0,
            'vehicle_ids[]': car_ids
        }

        print (str(data))

        self.session.post(url, data=data)

    def generate_missions(self):
        url = 'https://www.leitstellenspiel.de/mission-generate'
        try:
            self.session.get(url, headers={"X-CSRF-Token": self.authenticity_token, "User-Agent": self.headers["User-Agent"]})
        except Exception:
            logging.exception('error reloading missions')

    def parse_missing(self, missing_text):
        logging.debug('Enter parse_missing %s' % missing_text)
        if missing_text is None:
            return None

        regex = r'^ Wir benötigen noch min. \w+ Feuerwehrleute.$'
        if "Feuerwehrleute" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            logging.debug('Enter missing_text %s' % missing_text)
            missing_text = missing_text + "1 Löschfahrzeug"

        missing_text = missing_text.replace('Zusätzlich benötigte Fahrzeuge: ','')
        missing_text = missing_text.replace('(GW-L2 Wasser, SW 1000, SW 2000 oder Ähnliches)','')

        logging.debug('Enter missing_text %s' % missing_text)
        missing_text = missing_text.replace('.','')
        logging.debug('Enter missing_text %s' % missing_text)

        #vehicle_matches = re.findall('(?:[,.:]) (\d+) ([^,()]*?)(?: \([^()]*\))?(?=,|$)', missing_text)
        vehicles_matches = missing_text.split(",")
        logging.debug('Enter missing_text %s' % len(vehicles_matches))

        result = []

        for carrequest in vehicles_matches:
            print (carrequest)
            #carrequest = re.sub(r'\([^)]*\)', '', carrequest)
            #print ("Short " + carrequest)
            vehicle_matches = carrequest.split()
            logging.debug('Enter vehicle_matches %s' % vehicle_matches)
            vtype = self.lookup_vehicle_type_by_name(vehicle_matches[1])
            logging.debug('Enter vtype %s' % vtype)

            for i in range(int(vehicle_matches[0])):
                result.append(vtype)
        return result

    def parse_missing_rtw(self, patients_count):
        logging.debug('Enter parse_missing_rtw %s' % patients_count)
        if patients_count == 0:
            return None
        vtype = self.lookup_vehicle_type_by_name("RTW")
        logging.debug('Enter vtype %s' % vtype)

        for i in range(patients_count):
            result.append(vtype)
        return result

    def parse_missing_pol(self, prisoners_count):
        logging.debug('Enter parse_missing_pol %s' % prisoners_count)
        if patients_count == 0:
            return None
        vtype = self.lookup_vehicle_type_by_name("FuStW")
        logging.debug('Enter vtype %s' % vtype)

        for i in range(prisoners_count):
            result.append(vtype)
        return result

    def lookup_vehicle_type_by_name(self, name):
        if name in self.data['vehicle_type_names']:
            return self.data['vehicle_type_names'][name]
        else:
            logging.warning('unknown vehicle name: %s' % name)
            return 'unknown'

    def probe_need(self, missionid, avalible_cars):
        if len(avalible_cars) == 0:
            logging.info("no car avalible for probing")
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

    def hire_crew(self, id, days):
        self.session.get('https://www.leitstellenspiel.de/buildings/%s/hire_do/%d' % (id, days))
