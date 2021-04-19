import json
import pymongo
from pymongo import MongoClient

class DataOperations(object):
    
    def __init__(self):
        self.config = json.load(open("config.json"))
        self.mongo_client = MongoClient(str(self.config['mongo_ip']), 27017)
    
    def delete_data(self, data, collection_name):
        pass
    
    def create_final_data(self, data, collection_name):
        pass
    
    def get_final_data(self, collection_name):
        pass


if __name__ == '__main__':
    obj = DataOperations()
    