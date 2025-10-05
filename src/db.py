from tinydb import TinyDB, Query
import os

class Database:
    def __init__(self, db_path="data.json"):
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.db = TinyDB(db_path)
        self.flights = self.db.table("flights")
    
    def get_all_flights(self):
        return self.flights.all()
