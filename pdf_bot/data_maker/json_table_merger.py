import os
import json


class JsonMergerTables(object):
    def __init__(self):
        self.directory = "./table_jsons"

    def mergeFiles(self):
        final_json = []
        for filename in sorted(os.listdir(self.directory)):
            temp_json = []
            with open("table_jsons/" + filename, "r") as jsonHandle:
                temp_json = json.load(jsonHandle)

            if temp_json:
                final_json.extend(temp_json)
        
        with open("../data/json_table_merge_data.json", "w") as jsonHandle:
            json.dump(final_json, jsonHandle, indent=2)


if __name__ == '__main__':
    obj = JsonMergerTables()
    obj.mergeFiles()