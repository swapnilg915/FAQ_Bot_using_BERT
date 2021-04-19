import os
import json
import shutil
import traceback
from pymongo import MongoClient

class JsonMerger(object):

    def __init__(self):
        self.directory = "data_maker/json_files"
        self.table_directory = "data_maker/table_jsons"
        self.config = json.load(open('config.json'))
        self.mongo_client = MongoClient(str(self.config['mongo_ip']), 27017)


    def mergeFiles(self, data):
        table_data ={}
        print "\n inside json merger :: "
        final_json = []
        try:
            ######### add new data to existing data
            for fn in sorted(os.listdir(self.directory)):
                if fn.endswith('.json'):
                    temp_json = []
                    with open(self.directory + '/' + fn , "r") as jsonHandle:
                        temp_json = json.load(jsonHandle)
                    for dic in temp_json:
                        if 'all_childs' in dic:
                            dic.pop("all_childs")
                        final_json.append(dic)

            #### copy headings in variations field
            final_json_new = []
            for dic in final_json:
                if dic['tag_name'] != 'p':
                    dic['variations'] = []
                    dic['variations'].append(dic['text'])
                final_json_new.append(dic)
            final_json = final_json_new

            data['faq_data'] = final_json

            #### move solr json to processed jsons folder
            solr_json_name = data['solr_json_name']
            solr_json_path = data['solr_json_path']
            if not os.path.exists('data_maker/processed_jsons'):
                os.makedirs('data_maker/processed_jsons')
            moving_path = 'data_maker/processed_jsons/' + solr_json_name
            shutil.move(solr_json_path, moving_path)
            print "\n moved solr json to processed jsons folder :: "

            ######## table dump in mongo
            table_json_name = data['table_json_name']
            table_json_path = data['table_json_path']

            # reading file from table json
            #print "Inserting table data in mongo--->","--/"*25
            #import pdb;pdb.set_trace()
            for tfile in sorted(os.listdir(self.table_directory)):
                #print tfile,"--",table_json_name
                if tfile == table_json_name[1:]:
                    table_data = json.load(open(self.table_directory+'/'+tfile,'r'))
                    data['table_data'] = table_data
                    break
            # if table_data_collection.find().count()>0:
            #     mongoTdata = list(table_data_collection.find({},{'_id':0}))
            #     print len(mongoTdata),'<-----Length of tabledata'
            # print len(table_data),'<-----Length of tabledata'
            # table_data.extend(mongoTdata)
            # table_data_collection.insert_many(table_data)
            # print "INSERTED table data in_ mongo ",'--/'*25

            if not os.path.exists('data_maker/processed_table_jsons'):
                os.makedirs('data_maker/processed_table_jsons')
            moving_path = 'data_maker/processed_table_jsons/' + table_json_name
            shutil.move(table_json_path+table_json_name, moving_path)

        except Exception as e:
            print "\n Error in mergeFiles :: ",e,"\n",traceback.format_exc()

        return data

if __name__ == '__main__':
    obj = JsonMerger()
    obj.mergeFiles()
