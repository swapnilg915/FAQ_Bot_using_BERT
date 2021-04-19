import os
import json
import redis
import traceback

import gensim
from gensim import corpora, models, similarities
from gensim.models import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from gensim.similarities import WmdSimilarity

class DataLoader(object):

    def __init__(self):
        self.config = json.load(open('config.json'))
        self.redis_client = redis.StrictRedis(host=str(self.config['redis_ip']), port=6379, db=0)
        self.all_wmd_instances = {}
        self.load_wmd_on_search_restart()#### on search worker restart
        self.ttl = 604800

    def updateInRedisandgetWMDcorpus(self, data_flag, data, load_flag = ""):
        try:
            # print "\n data => ",json.dumps(data)
            redis_key = str(data['tenant_id']) + '_' + str(data['bot_id'])+'_wmd_data'
            print '\n redis_key ==>> ',redis_key
            redis_data = {}
            if load_flag:
                if data:
                    redis_data = json.loads(self.redis_client.get(redis_key))
                    print '\n redis_data => ',redis_data
                    self.all_wmd_instances[redis_key] = {}
                if redis_data['new_file_flag']:
                    wmd_model = self.load_wmd(data_flag, data)
                    if data_flag in self.all_wmd_instances[redis_key]:
                        self.all_wmd_instances.pop(self.all_wmd_instances[redis_key][data_flag])
                    self.all_wmd_instances[redis_key][data_flag] = wmd_model
                    redis_data['new_file_flag'] = False
                    # print "redis_data========>",redis_data
                    self.redis_client.setex(redis_key,self.ttl,json.dumps(redis_data))
        
                elif (redis_key not in self.all_wmd_instances) or (data_flag not in self.all_wmd_instances[redis_key]):
                    wmd_model = self.load_wmd(data_flag, data)
                    self.all_wmd_instances[redis_key][data_flag] = wmd_model
                    redis_data['new_file_flag'] = False
                    # print "redis_data========>",redis_data
                    self.redis_client.setex(redis_key,self.ttl,json.dumps(redis_data))
                # print self.all_wmd_instances
                return {}
            else:
                if (redis_key not in self.all_wmd_instances) or (data_flag not in self.all_wmd_instances[redis_key]):
                    wmd_model = self.load_wmd(data_flag, data)
                    self.all_wmd_instances[redis_key][data_flag] = wmd_model
                    redis_data['new_file_flag'] = False
                    # print "redis_data========>",redis_data
                    self.redis_client.setex(redis_key,self.ttl,json.dumps(redis_data))

                return self.all_wmd_instances[redis_key][data_flag]
            
        except Exception as e:
            print "\n Error in updateInRedisandgetWMDcorpus :: ",e,"\n",traceback.format_exc()
    
    def load_wmd_on_search_restart(self):
        key_lis = []
        data_flag = ['variations','sentences']
        root_dir = os.getcwd()
        root_dir = root_dir +"/data/"
        for key in self.redis_client.scan_iter("*_wmd_data"):
            key_lis.append(key)
        print "\n keys in redis===>",key_lis
        for each in key_lis:
            path = ""
            self.all_wmd_instances[each] = {}
            all_data = each.split("_")
            tid = all_data[0]
            bot_id = all_data[1]
            for flags in data_flag:
                path = root_dir+str(tid)+"_"+str(bot_id)+"_trained_models/wmd_trained_pickle_"+flags
                if os.path.isfile(path):
                    self.all_wmd_instances[each][flags] = self.load_wmd_search_worker(path)
                    print "\n loaded wmd model for::", each," ",flags
                else:
                    print "\n no wmd model for ::",each," ",flags
            
    
    def getAtd(self, data):
        self.all_trained_data = {}
        folder_path = "data/training_data/" + str(data['db_name'])
        if os.path.exists(folder_path + '/all_trained_data.pickle'):
            with open(folder_path + '/all_trained_data.pickle', 'rb') as all_trained_data:
                self.all_trained_data = pickle.load(all_trained_data)
        # print "\n trained data loaded = ",self.all_trained_data
        
    def load_wmd_search_worker(self,path):
        WMD_PATH = path
        trained_wmd_model = gensim.similarities.docsim.Similarity.load(WMD_PATH)
        # print "\n loaded wmd model :: "
        return trained_wmd_model

    def load_wmd(self,data_flag, data):#######thissssssssssss
        folder_name = 'data/' + str(data['tenant_id']) + '_' + str(data['bot_id']) + '_trained_models'

        WMD_PATH = folder_name +'/wmd_trained_pickle_'+ data_flag
        trained_wmd_model = gensim.similarities.docsim.Similarity.load(WMD_PATH)
        print "\n loaded wmd model :: "
        return trained_wmd_model


if __name__ == '__main__':
    obj = DataLoader()
    # obj.mergeFiles()
