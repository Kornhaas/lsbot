import sqlite3


class DBWrapper:
    def __init__(self, filename):
        self.db = sqlite3.connect(filename)
        self.c = self.db.cursor()

        # init db
        self.c.execute('CREATE TABLE IF NOT EXISTS periodic_tasks (name TEXT PRIMARY KEY, last_run INTEGER);')
        self.db.commit()

    def get_task_last_run(self, task_name):
        self.c.execute('SELECT last_run FROM periodic_tasks WHERE name=?', (task_name,))
        result = self.c.fetchone()
        if result is None:
            return None
        return result[0]

    def write_task_last_run(self, name, last_run):
        self.c.execute('INSERT OR REPLACE INTO periodic_tasks(name, last_run) VALUES(?, ?)', (name, last_run))
        self.db.commit()
