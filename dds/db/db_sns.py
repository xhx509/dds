import os
import sqlite3
import time


class DbSNS:
    def __init__(self, name):
        self.name = name

    def db_get(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS loggers\
            ( \
            id              INTEGER PRIMARY KEY, \
            mac             TEXT, \
            time            INTEGER, \
            desc            TEXT, \
            served          INTEGER \
            )"
        )
        db.commit()
        c.close()
        db.close()

    def db_exists(self):
        return os.path.isfile(self.name)

    def db_empty(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('DELETE FROM loggers')
        db.commit()
        c.close()
        db.close()

    def db_deletion(self):
        try:
            os.remove(self.name)
            return 0
        except (FileNotFoundError, Exception) as ex:
            print(ex)
            return 1

    def add_logger(self, m, t, d, s):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('INSERT INTO loggers('
                  'mac, time, desc, served) '
                  'VALUES(?,?,?,?)',
                  (m, t, d, s))
        db.commit()
        c.close()
        db.close()

    def _get_record_id_by_mac(self, m):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT id from loggers WHERE mac=?', (m, ))
        records = c.fetchall()
        c.close()
        db.close()
        if not records:
            return
        return records[0][0]

    def list_all_records(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT * from loggers')
        records = c.fetchall()
        c.close()
        db.close()
        return records

    def get_records_by_non_served(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        s = 'SELECT * from loggers WHERE served=0'
        c.execute(s)
        records = c.fetchall()
        c.close()
        db.close()
        if not records:
            return []
        return records

    def count_records_by_served(self, s):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT Count(*) FROM loggers WHERE served=?', (s, ))
        r = c.fetchall()
        c.close()
        db.close()
        return r[0][0]

    def dump_records_as_string(self):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT * from loggers')
        records = c.fetchall()
        c.close()
        db.close()
        s = ''
        for _ in records:
            # (1, 'mac_1', 1232123, 'description', 'served')
            s += '{} {} {} / '.format(_[1], _[2], _[3])
        return s

    def does_record_exist(self, m, t, d):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT EXISTS(SELECT 1 from loggers WHERE mac=? '
                  'AND time=? AND desc=?)', (m, t, d, ))
        records = c.fetchall()
        c.close()
        db.close()
        return records[0][0]

    def get_record_id(self, m, t, d):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('SELECT id from loggers WHERE mac=? '
                  'AND time=? AND desc=?', (m, t, d, ))
        records = c.fetchall()
        c.close()
        db.close()
        return records[0][0]

    def delete_record(self, record_id):
        db = sqlite3.connect(self.name)
        c = db.cursor()
        c.execute('DELETE FROM loggers where id=?', (record_id,))
        db.commit()
        c.close()
        db.close()

    def mark_as_served(self, m, t, d):
        if self.does_record_exist(m, t, d):
            i = self.get_record_id(m, t, d)
            self.delete_record(i)
        self.add_logger(m, t, d, 1)
