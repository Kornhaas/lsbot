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

    def get_all_radiodata(self):
        r = self.session.get('https://www.leitstellenspiel.de/')
        radioMessage_json = re.findall('radioMessage\((.*?)\);', r.text)
        radioMessage = {}
        for r in radioMessage_json:
            radioMessage = json.loads(r)
            #radioMessage['id'] = str(radioMessage['id'])
            #radioMessage[radioMessage['id']] = radioMessage
        return radioMessage

    def get_all_patientdata(self, missionid):
        p = self.session.get('https://www.leitstellenspiel.de/missions/%s' % missionid)
        patient_json = re.findall('patientBarColor\((.*?)\);', p.text)
        patient = {}
        for p in patient_json:
            patient = json.loads(p)
            patient['id'] = str(patient['id'])
            patient[patient['id']] = patient
        return patient


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

        #regex = r'^ Wir benötigen noch min. \w+ Feuerwehrleute.$'
        regex = r'(Wir benötigen noch min. \w+ Feuerwehrleute.$)'
        if "Feuerwehrleute" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            missing_text = missing_text + ", 1 Löschfahrzeug (LF),"

        regex = r'( Wir benötigen noch min \w+ Personen mit Dekon-P Ausbildung$)'
        if "Dekon-P" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            missing_text = missing_text + ", 1 Dekon-P (DEKON-P),"

        regex = r'( Wir benötigen min. \w+ Personen mit GW-Wasserrettung Ausbildung.$)'
        if "GW-Wasserrettung" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            missing_text = missing_text + ", 1 GW-Wasserrettung (GWWa),"

        regex = r'(Wir benötigen noch min. \w+ Feuerwehrmann.$)'
        if "Feuerwehrmann" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            missing_text = missing_text + ", 1 Löschfahrzeug (LF),"

        regex = r'(\w+ l. Wasser)'
        if "l. Wasser" in missing_text:
            missing_text = re.sub(regex, '', missing_text)
            missing_text = missing_text + ", 2 Tanklöschfahrzeuge (TLF),"

        missing_text = missing_text.replace('Zusätzlich benötigte Fahrzeuge: ','')
        missing_text = missing_text.replace('(GW-L2 Wasser, SW 1000, SW 2000 oder Ähnliches)','')

        missing_text = missing_text.replace('.','')
        missing_text = missing_text.replace(',,',',')
        missing_text = missing_text.replace(',  ,',',')

        if missing_text.endswith(','):
            missing_text = missing_text[:-1]


        logging.debug('Enter missing_text :%s' % missing_text)

        vehicles_matches = missing_text.split(",")
        logging.debug('Enter vehicles_matches :%s' % str(vehicles_matches))
        result = []

        for carrequest in vehicles_matches:

            if str(carrequest) is " " or str(carrequest) is "" or str(carrequest) is None :
                continue

            vehicle_matches = carrequest.split()

            #Special Handling for ELW 1 or ELW 2
            if vehicle_matches[1] == "ELW":
                vehicle_matches[1] = vehicle_matches[1] + " " +vehicle_matches[2]

            if vehicle_matches[1] == "LKW":
                vehicle_matches[1] = vehicle_matches[1] + " " +vehicle_matches[2]

            vtype = self.lookup_vehicle_type_by_name(vehicle_matches[1])
            logging.debug('Enter vtype %s' % vtype)

            for i in range(int(vehicle_matches[0])):
                result.append(vtype)
        return result

    def parse_missing_pol(self, prisoners_count):
        logging.debug('Enter parse_missing_pol %s' % prisoners_count)
        if prisoners_count == 0:
            return None
        result = []

        carrequest = str(prisoners_count) + " FuStW"
        vehicle_matches = carrequest.split()

        vtype = self.lookup_vehicle_type_by_name(vehicle_matches[1])
        logging.debug('Enter vtype %s' % vtype)

        for i in range(int(vehicle_matches[0])):
            result.append(vtype)
        return result

    def lookup_vehicle_type_by_name(self, name):
        logging.debug('Enter lookup_vehicle_type_by_name %s' % name)
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
        self.share_mission_in_alliance(missionid)

    def recall_car_from_mission(self, carid):
        self.session.get('https://www.leitstellenspiel.de/vehicles/%s/backalarm?return=mission' % carid)

    def share_mission_in_alliance(self, missionid):
        logging.debug('Enter share_mission_in_alliance %s' % missionid)
        #self.session.get('https://www.leitstellenspiel.de/missions/%s/alliance' % missionid)

    def send_release_prisoner(self, missionid):
        logging.info('https://www.leitstellenspiel.de/missions/%s/gefangene/entlassen' % missionid)
        url = 'https://www.leitstellenspiel.de/missions/%s/gefangene/entlassen' % missionid
        data = {
            'authenticity_token': self.authenticity_token
        }
        self.session.post(url, data=data)

    def send_release_patient(self, carid):
        logging.info('https://www.leitstellenspiel.de/vehicles/%s/patient/-1' % carid)

        # Last way out - Remove the guy from the car
        self.session.get('https://www.leitstellenspiel.de/vehicles/%s/patient/-1' % carid)

    def lookup_vehicle_type_ids(self, type):
        if type in self.data['vehicle_type_ids']:
            return self.data['vehicle_type_ids'][type]
        else:
            raise AttributeError('unknown vehicle type: %s' % type)

    def hire_crew(self, id, days):
        self.session.get('https://www.leitstellenspiel.de/buildings/%s/hire_do/%d' % (id, days))
