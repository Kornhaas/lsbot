import sqlite3
import logging


class DBWrapper:
    def __init__(self, filename):
        self.db = sqlite3.connect(filename)
        self.db.row_factory = sqlite3.Row
        self.c = self.db.cursor()

        # init db
        self.c.execute("CREATE TABLE IF NOT EXISTS periodic_tasks (name TEXT PRIMARY KEY, last_run INTEGER);")
        self.c.execute("""CREATE TABLE IF NOT EXISTS missions(
                    id int primary key,
                    caption TEXT,
                    status TEXT default 'NEW' not null,
                    user_id int,
                    sw int,
                    sw_start_in int,
                    missing_text TEXT,
					prisoners_count int,
					patients_count int,
                    check (status in ('NEW','MISSING', 'MISSING_POL', 'MISSING_RTW','DRIVING','ONGOING','FINISHED'))
                );""")
				#Prisoners and patients count added to handle the cases
        self.db.commit()

    def get_task_last_run(self, task_name):
        self.c.execute('SELECT last_run FROM periodic_tasks WHERE name=?', [task_name])
        result = self.c.fetchone()
        if result is None:
            return None
        return result[0]

    def write_task_last_run(self, name, last_run):
        self.c.execute('INSERT OR REPLACE INTO periodic_tasks(name, last_run) VALUES(?, ?)', [name, last_run])
        self.db.commit()

    def get_current_missions(self):
        self.c.execute("SELECT * FROM missions WHERE status IS NOT 'FINISHED'")
        result = self.c.fetchall()
        if result is None:
        #    logging.debug('get_current_missions empty' )
            return []
        #logging.debug('get_current_missions' + str(result))
        return result

    def get_missions_by_status(self, status):
        self.c.execute("SELECT * FROM missions WHERE status=?", [status])
        result = self.c.fetchall()
        if result is None:
            return []
        #logging.debug('get_missions_by_status' + str(result))
        return result

    def get_mission(self, id):
        self.c.execute("SELECT * FROM missions WHERE id=?", [id])
        #logging.debug('get_mission' + str(self.c.fetchone()))
        return self.c.fetchone()

    def write_mission(self, mission):
        self.c.execute('INSERT OR REPLACE INTO missions(id, caption, status, user_id, sw, sw_start_in, missing_text)'
                       'VALUES(:id, :caption, :status, :user_id, :sw, :sw_start_in, :missing_text)',
                       mission)
        self.db.commit()
