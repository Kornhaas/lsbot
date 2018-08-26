import sqlite3


class DBWrapper:
    def __init__(self, filename):
        self.db = sqlite3.connect(filename)
        self.c = self.db.cursor()

        # init db
        self.c.execute('CREATE TABLE IF NOT EXISTS periodic_tasks (name TEXT PRIMARY KEY, last_run INTEGER);')
        self.c.execute("CREATE TABLE IF NOT EXISTS missions (id INTEGER PRIMARY KEY, name TEXT,"
                       "status TEXT CHECK(status in ('NEW','FINISHED')));")
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
        self.c.execute("SELECT id, name, status FROM missions WHERE status IS NOT 'FINISHED'")
        result = self.c.fetchall()
        if result is None:
            return []
        return [{'id': i[0], 'name': i[1], 'status': i[2]} for i in result]

    def get_mission(self, id):
        self.c.execute("SELECT * FROM missions WHERE id=?", [id])
        return self.c.fetchone()

    def write_mission(self, mission):
        self.c.execute('INSERT OR REPLACE INTO missions(id, name, status) VALUES(:id, :name, :status)', mission)
        self.db.commit()

    def update_mission_status(self, id, status):
        self.c.execute('UPDATE missions SET status=? WHERE id= ?', [status, id])
        self.db.commit()
