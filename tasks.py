import logging
from LeitstellenAPI import LeitstellenAPI
from DBWrapper import DBWrapper
from time import sleep


class AbstractPeriodicTask:
    def __init__(self):
        raise NotImplementedError()

    def get_name(self) -> str:
        raise NotImplementedError()

    def get_wait_time(self) -> str:
        raise NotImplementedError()

    def run(self, ls: LeitstellenAPI, db: DBWrapper):
        raise NotImplementedError()


class CrewHirer(AbstractPeriodicTask):
    def __init__(self):
        pass

    def get_name(self):
        return 'HIRE CREW'

    def get_wait_time(self):
        return 24*60*60

    def run(self, ls, db):
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
        return 10

    def run(self, ls, db):
        ls.generate_missions()


class MissionController(AbstractPeriodicTask):
    def __init__(self):
        pass

    def get_name(self):
        return 'CONTROL MISSIONS'

    def get_wait_time(self):
        return 30

    def run(self, ls, db):
        missions = ls.get_all_missions()

        # if a previous mission isnt in the missions anymore, set its status in the db to finished
        db_missions = db.get_current_missions()
        for m in db_missions:
            if str(m['id']) not in missions.keys():
                logging.info('finished mission: %s' % m['caption'])
                db.update_mission_status(m['id'], 'FINISHED')

        # add new missions to the db and update old ones
        for key, m in missions.items():
            dbm = db.get_mission(m['id'])
            if dbm is None:
                logging.info('new mission: %s' % m['caption'])
                m['status'] = 'NEW'
            if m['vehicle_state'] == 1:
                m['status'] = "DRIVING"
            elif m['missing_text'] is not None:
                m['status'] = "MISSING"
            elif m['vehicle_state'] == 2:
                m['status'] = "ONGOING"
            if 'status' not in m:
                logging.warning('UNKNOWN STATUS IN MISSION %s: "%s"' % (m['id'], m['caption']))
                m['status'] = "NEW"
            db.write_mission(m)

        # temp hack: filter out verband-missions so that resources dont get stuck on unmanagable big missions
        # also filter 'sw' missions (with a timer, because they also take up vehicles for to much time)
        # todo better filter criteria
        for k in list(missions):
            if missions[k]['user_id'] != ls.user['id'] or missions[k]['sw']:
                del missions[k]

        for id, m in missions.items():
            details = ls.get_mission_details(id)
            if not details['vehicles']['driving']:  # only work with missions with no cars currently driving to them
                if m['missing'] is not None:
                    avalible_cars = details['vehicles']['avalible']
                    need_help = False
                    car_ids = []
                    for missing_type in m['missing']:
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
                    # todo deal with missing crew
                    if need_help:
                        # todo open mission for verband
                        pass
                    if len(car_ids) > 0:
                        ls.send_cars_to_mission(id, car_ids)
                        logging.info('sent cars to mission: %s' % m['caption'])
                        sleep(2)
                elif not details['vehicles']['at_mission']:
                    # no stated need and no vehicles at mission: probe need
                    logging.info('probe need for: %s' % m['caption'])
                    ls.probe_need(id, details['vehicles']['avalible'])
                    sleep(2)
