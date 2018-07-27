# coding=utf-8

from time import strftime
import requests
from lxml.html import fromstring
from bs4 import BeautifulSoup

class LeitstellenAPI:
    html = ''
    authenticity_token = ''
    status = ''
    cars = {}
    fireman_at_accident = 0
    session = None

    missingcases = {
        'Loeschfahrzeug (LF)': 'LF 20/16',
        'Loeschfahrzeuge (LF)': 'LF 20/16',
        'Feuerwehrleute': 'LF 20/16',
        'FuStW': 'FuStW',
        'ELW 1': 'ELW 1',
        'ELW 2': 'ELW 2',
        'Drehleitern (DLK 23)': 'DLK 23',
        'GW-Messtechnik': 'GW-Messtechnik',
        'GW-A oder AB-Atemschutz': 'GW-A',
        'Ruestwagen oder HLF': 'RW',
        'GW-Oel': u'GW-Öl',
        'GW-Gefahrgut': 'GW-Gefahrgut',
        'GW-Hoehenrettung': u'GW-Höhenrettung',
        'Schlauchwagen (GW-L2 Wasser': 'SW Kats',
        '': ''
    }
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

        url = "https://www.leitstellenspiel.de/users/sign_in"
        r = self.session.post(url)

        login_page = BeautifulSoup(r.content, 'html.parser')
        self.authenticity_token = login_page.find('input', {'name': 'authenticity_token'}).get('value')

        data = {
            'authenticity_token': self.authenticity_token,
            'user[email]': self.email,
            'user[password]': self.password,
            'user[remember_me]': 1,
            'commit': 'Einloggen'
        }

        r = self.session.post(url, data=data)
        login_page = BeautifulSoup(r.content, 'html.parser')
        self.authenticity_token = login_page.find('input', {'name': 'authenticity_token'}).get('value')
        username = login_page.find('a', {'id': 'navbar_profile_link'}).text[1:]

        print(strftime("%H:%M:%S") + ': Erfolgreich Eingeloggt als ' + username)

    def get_all_accidents(self):
        mission = self.session.get('https://www.leitstellenspiel.de/')
        startpoint = mission.text.find('missionMarkerAdd')
        endpoint = mission.text.find('missionMarkerBulkAdd', startpoint)
        ids = mission.text[startpoint:endpoint]
        ids = ids.split('\n')

        i = 0

        accidents = {}

        while i < len(ids) - 1:
            idpoint = ids[i].find(',"id":')
            statusstartpoint = ids[i].find(',"icon":')
            statusendpoint = ids[i].find(',"caption":', statusstartpoint)
            missingstartpoint = ids[i].find(',"missing_text":')
            missingendpoint = ids[i].find(',"id":', missingstartpoint)
            namestartpoint = ids[i].find(',"caption":')
            nameendpoint = ids[i].find(',"captionOld":', namestartpoint)

            t = 0
            missingarray = {}

            if 'Feuerwehrleute' in ids[i][missingstartpoint + 16: missingendpoint]:
                missing = ids[i][missingstartpoint + 16: missingendpoint][1:].split(',')

                while t < len(missing):
                    if missing[t][2:][-1:] == '"':
                        missingarray[int(missing[t][24:26])] = missing[t][27:-2]
                    else:
                        missingarray[int(missing[t][24:26])] = missing[t][27:-1]
                    t = t + 1
            else:
                missing = ids[i][missingstartpoint + 16: missingendpoint][43:].split(',')

                while t < len(missing):
                    if missing[t][2:][-1:] == '"':
                        missingarray[missing[t][:2]] = missing[t][2:][:-1]
                    else:
                        missingarray[missing[t][:2]] = missing[t][2:]
                    t = t + 1

            accidents[ids[i][idpoint + 6: idpoint + 15]] = {
                'status': ids[i][statusstartpoint + 8: statusendpoint][-4:-1],
                'missing': missingarray,
                'name': str(ids[i][namestartpoint + 10: nameendpoint][1:])
                    .replace("\u00fc", "ü")
                    .replace("\u00f6", "ö")
                    .replace("\u00d6", "Ö")
                    .replace("\u00df", "ß")
                    .replace("\u00e4", "ä")
                    .replace("\u00c4", "Ä"),
                'vehicle_state': ''
            }
            i = i + 1
        return accidents

    def get_accident(self, accidentid, accident):
        mission = self.session.get('https://www.leitstellenspiel.de/missions/' + accidentid)

        if not self.parse_cars_needed(mission.text):
            return

        self.parse_available_cars(mission.text)

        if accident['missing'] != {'': ''}:
            for count, string in accident['missing'].iteritems():
                string = str(string).replace("\u00f6", "oe")
                string = string.replace("\u00d6", "Oe")
                string = string.replace("\u00fc", "ue")

                if string[0] == ' ':
                    string = string[1:]

                t = 0

                if string == 'Feuerwehrleute':
                    self.parse_fireman_at_accident(mission.text)
                    try:
                        newcount = (int(count) - int(self.fireman_at_accident)) // 9 + 1
                    except ValueError:
                        newcount = 0

                    while t < newcount:
                        for carid, cartype in self.cars.items():
                            if cartype == self.missingcases[string] and carid in self.cars:
                                self.send_car_to_accident(accidentid, carid)
                                del self.cars[carid]
                                print(strftime("%H:%M:%S") + ': ' + cartype + ' zu ' + accident['name'] + ' alarmiert')
                                t = t + 1
                                break
                else:
                    try:
                        newcount = int(count)
                    except ValueError:
                        newcount = 0

                    while t < newcount:
                        for carid, cartype in self.cars.items():
                            if cartype == self.missingcases[string] and carid in self.cars:
                                self.send_car_to_accident(accidentid, carid)
                                del self.cars[carid]
                                print(strftime("%H:%M:%S") + ': ' + cartype + ' zu ' + accident['name'] + ' alarmiert')
                                t = t + 1
                                break
        else:
            if accident['status'] == 'rot':
                for key, value in self.cars.items():
                    if value == 'LF 20/16':
                        self.send_car_to_accident(accidentid, key)
                        print(strftime("%H:%M:%S") + ': ' + value + ' zu ' + accident['name'] + ' alarmiert')
                        break

    @staticmethod
    def parse_cars_needed(html):
        tree = fromstring(html)
        vehicle_state = tree.xpath('//h4[@id="h2_vehicle_driving"]//text()')

        if vehicle_state == ['Fahrzeuge auf Anfahrt']:
            return False
        else:
            return True

    def parse_fireman_at_accident(self, html):
        tree = fromstring(html)
        people = tree.xpath('//div[small[contains(., "Feuerwehrleute")]]/small//text()')
        for value in people:
            if value[11:-15] == 'Feuerwehrleute':
                self.fireman_at_accident = value[38:]

    def parse_available_cars(self, html):
        tree = fromstring(html)
        cars = tree.xpath('//tr[@class="vehicle_select_table_tr"]/@id')
        types = tree.xpath('//tr[@class="vehicle_select_table_tr"]/@vehicle_type')

        self.cars = {}

        for i, value in enumerate(cars):
            self.cars[value[24:]] = types[i]

    def send_car_to_accident(self, accident, car):
        url = 'https://www.leitstellenspiel.de/missions/' + accident + '/alarm'
        data = {
            'authenticity_token': self.authenticity_token,
            'commit': 'Alarmieren',
            'next_mission': 0,
            'vehicle_ids[]': car
        }

        self.session.post(url, data=data)
