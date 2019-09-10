import logging
import json
from LeitstellenAPI import LeitstellenAPI
from DBWrapper import DBWrapper
from time import sleep


class AbstractPeriodicTask:
    def __init__(self):
        raise NotImplementedError()

    def get_name(self):
        raise NotImplementedError()

    def get_wait_time(self):
        raise NotImplementedError()

    def run(self, ls, db):
        raise NotImplementedError()


class CrewHirer(AbstractPeriodicTask):
    def __init__(self):
        pass

    def get_name(self):
        return 'HIRE CREW'

    def get_wait_time(self):
        return 24*60*60

    def run(self, ls, db, supportcommunity):
        logging.info('hire crew in every building')
        all_buildings = ls.get_all_buildings()
        for id, b in all_buildings.items():
            if b['user_id'] == ls.user['id'] and b['personal_count'] > 0:
                ls.hire_crew(id, 3)


class MissionGenerator(AbstractPeriodicTask):
    def __init__(self):
        pass

    def get_name(self):
        return 'GENERATE MISSIONS'

    def get_wait_time(self):
        return 20

    def run(self, ls, db, supportcommunity):
        ls.generate_missions()


class MissionController(AbstractPeriodicTask):
    def __init__(self):
        pass

    def get_name(self):
        return 'CONTROL MISSIONS'

    def get_wait_time(self):
        return 30

    def run(self, ls, db, supportcommunity):
        print("load_missions_into_db")
        load_missions_into_db(ls, db)
        print("probe_new_missions")
        probe_new_missions(ls, db, supportcommunity)
        print("load_missions_into_db")
        load_missions_into_db(ls, db)
        print("send_missing_cars")
        send_missing_cars(ls, db, supportcommunity)
        print("load_missions_into_db")
        load_missions_into_db(ls, db)


def load_missions_into_db(ls, db):
    missions = ls.get_all_missions()

    # if a previous mission isnt in the missions anymore, set its status in the db to finished
    db_missions = db.get_current_missions()

    for m in db_missions:
        if str(m['id']) not in missions.keys():
            logging.info('finished mission: %s' % m['caption'])
            m = dict(m)
            m['status'] = 'FINISHED'
            m['missing_text'] = None
            m['missing_text_short'] = None
            db.write_mission(m)

    # add new missions to the db and update old ones
    for key, m in missions.items():
        dbm = db.get_mission(m['id'])
        if dbm is None:
            logging.info('new mission: %s' % m['caption'])
            m['status'] = 'NEW'
        if m['vehicle_state'] == 1:
            m['status'] = "DRIVING"
        elif m['missing_text'] is not None and "red" not in m['icon']:
            if m['user_id'] is not None:
                m['status'] = "MISSING"
            else:
                m['status'] = 'NEW'
        elif m['prisoners_count'] != 0 and "red" not in m['icon']:
            m['status'] = "MISSING_POL"
        elif m['patients_count'] != 0 and "red" not in m['icon']:
            m['status'] = "MISSING_RTW"
        elif m['vehicle_state'] == 2:
            m['status'] = "ONGOING"
        elif dbm is not None and dbm['status'] == 'NEW':
            m['status'] = 'NEW'
        elif 'status' not in m:
            logging.warning('UNKNOWN STATUS IN MISSION %s: "%s"' % (m['id'], m['caption']))
            m['status'] = "NEW"
        db.write_mission(m)


def probe_new_missions(ls, db, supportcommunity):
    missions = db.get_missions_by_status('NEW')
    for m in missions:
        logging.info('probe need for: %s' % m['caption'])
        if supportcommunity == 'FALSE':
            if m['user_id'] is None or m['user_id'] is "" or m['user_id'] is " ":
                continue

        details = ls.get_mission_details(m['id'])
        #print (str(details))
        ls.probe_need(m['id'], details['vehicles']['avalible'])
        sleep(2)


def send_missing_cars(ls, db, supportcommunity):
    missions = db.get_missions_by_status('MISSING')

    # check for prisoners call
    for m in missions:
         #Gefangene sollen abtransportiert werden.
        if "abtransportiert" in m['missing_text']:
            logging.debug('Enter gefangene/entlassen %s' % m['id'])
            ls.send_release_prisoner(m['id'])

    # check for radiomessages
    for m in missions:
        radiodata = ls.get_all_radiodata()
        if len(radiodata) != 0:
            for key, r in radiodata.items():
                if key == 'id':
                    logging.debug('Patient entlassen %s' % m['id'])
                    ls.send_release_patient(r)

    for m in missions:
        if not m['sw'] and m['user_id'] == ls.user['id'] and "abtransportiert" not in m['missing_text'] and supportcommunity == 'FALSE':
            send_cars_to_hospital(ls, db, m)
        elif "abtransportiert" not in m['missing_text'] and supportcommunity == 'TRUE':
            send_cars_to_hospital(ls, db, m)

    missions = db.get_missions_by_status('MISSING_RTW')

    for m in missions:
        if not m['sw'] and m['user_id'] == ls.user['id'] and supportcommunity == 'FALSE':
            send_rescue_cars(ls, db, m)
        elif supportcommunity == 'TRUE':
            send_rescue_cars(ls, db, m)

    missions = db.get_missions_by_status('MISSING_POL')

    for m in missions:
        if not m['sw'] and m['user_id'] == ls.user['id'] and supportcommunity == 'FALSE':
            send_police_cars(ls, db, m)
        elif supportcommunity == 'TRUE':
            send_police_cars(ls, db, m)

def send_cars_to_hospital(ls, db, m):
    print ("DEBUG" + str(m['id']))
    details = ls.get_mission_details(m['id'])

    avalible_cars = details['vehicles']['avalible']

    need_help = False
    car_ids = []
    missing = ls.parse_missing(m['missing_text'])
    print ("DEBUG" + str(m['missing_text']))
    print ("DEBUG" + str(missing))

    for missing_type in missing:
        type_ids = ls.lookup_vehicle_type_ids(missing_type)
        found_car = False
        for car in avalible_cars:
            if car['type_id'] in type_ids:
                car_ids.append(car['id'])
                avalible_cars.remove(car)
                found_car = True
                break
        if not found_car:
            need_help = True
    if len(car_ids) > 0:
        ls.send_cars_to_mission(m['id'], car_ids)
        logging.info('sent cars to mission: %s' % m['caption'])
        sleep(2)

def send_rescue_cars(ls, db, m):
    details = ls.get_mission_details(m['id'])
    patientdata = ls.get_all_patientdata(m['id'])
    patient_missing_text = None

    if len(patientdata) != 0:
        if "None" in str(patientdata['missing_text']) and int(patientdata['target_percent']) == 0 and "gruen" not in m['icon']:
            patient_missing_text = " 1 RTW (RTW),"
            logging.debug('Patient Nachforderung %s' % str(patient_missing_text))
        if "RTW" in str(patientdata['missing_text']):
            patient_missing_text = " 1 RTW (RTW),"
            logging.debug('Patient Nachforderung %s' % str(patient_missing_text))
        if "Tragehilfe" in str(patientdata['missing_text']):
            patient_missing_text = " 1 Löschfahrzeug (LF),"
            logging.debug('Patient Nachforderung %s' % str(patient_missing_text))
        if "NEF" in str(patientdata['missing_text']):
            patient_missing_text = " 1 NEF (NEF),"
            logging.debug('Patient Nachforderung %s' % str(patient_missing_text))

        if patient_missing_text is not None:
            avalible_cars = details['vehicles']['avalible']
            need_help = False
            car_ids = []
            missing = ls.parse_missing(patient_missing_text)

            for missing_type in missing:
                type_ids = ls.lookup_vehicle_type_ids(missing_type)
                found_car = False
                for car in avalible_cars:
                    if car['type_id'] in type_ids:
                        car_ids.append(car['id'])
                        avalible_cars.remove(car)
                        found_car = True
                        break
                if not found_car:
                    need_help = True
            if len(car_ids) > 0:
                ls.send_cars_to_mission(m['id'], car_ids)
                logging.info('sent cars to mission: %s' % m['caption'])
                sleep(2)


def send_police_cars(ls, db, m):
    details = ls.get_mission_details(m['id'])

    avalible_cars = details['vehicles']['avalible']

    need_help = False
    car_ids = []
    missing = ls.parse_missing_pol(m['prisoners_count'])

    for missing_type in missing:
        type_ids = ls.lookup_vehicle_type_ids(missing_type)
        found_car = False
        for car in avalible_cars:
            if car['type_id'] in type_ids:
                car_ids.append(car['id'])
                avalible_cars.remove(car)
                found_car = True
                break
        if not found_car:
            need_help = True

    if len(car_ids) > 0:
        ls.send_cars_to_mission(m['id'], car_ids)
        logging.info('sent cars to mission: %s' % m['caption'])
        sleep(2)
