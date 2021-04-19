#!/usr/local/bin/python
# coding: UTF8

import json
import re
from glob2 import glob
import os
import subprocess
from pymongo import MongoClient
import nltk
from nltk.corpus import stopwords
import snowballstemmer
import traceback
import copy
import gearman
import shutil
from collections import OrderedDict
import sys
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from pattern.en import lemma as lem
reload(sys)
sys.setdefaultencoding('utf-8')

### import scripts
from helper.keywords_maker import text_extract
from helper.spell_checker_script import SpellChecker
from helper.spacy_focus_words import FocusWords
from helper.synomyms_finder import FindSynonym
from helper.average_word import AverageWords

# for disambiguation, synonym and acronym
from worker.disambi_dict import disambiguation
from query_decider.query_create_training_data import QueryCreateTrainingData

# for keywordmatcher
from helper.keyword_matcher_new import NewKeywordMatcher

from hindi.hindi_preprocessor import HindiPreprocessor
from difflib import SequenceMatcher


class insertData(object):
    def __init__(self):
        self.config = json.load(open("config.json"))
        self.normalize_mapping = json.load(open("data/normalize_mapping.json"))
        self.server_ip = str(self.config['serverip'])
        self.mongo_client = MongoClient(str(self.config['mongo_ip']), 27017)
        self.gm_client = gearman.GearmanClient(['localhost:4730'])
        self.blockList = json.load(open('data/block_lem_words.json'))
        self.vectorizer = TfidfVectorizer(sublinear_tf=True, use_idf = True, max_df = 0.8)
        self.stopwords = stopwords.words('english')
        self.avg_words_obj = AverageWords()
        self.disambi_obj = disambiguation()
        self.query_create_training_data = QueryCreateTrainingData()
        self.keymatch_obj = NewKeywordMatcher()
        self.hindi_preprocessor_obj = HindiPreprocessor()
        self.temp_file = json.load(open('new_var.json'))

    def InsertinMongo(self, data, faq_data, doc_name, insert_id, coll_name):

        db_name = data['db_name']
        region = []
        if 'region' in data:region = data['region']
        try:
            faq_data_collection = self.mongo_client[data['db_name']][coll_name]
            if faq_data_collection.find({"$or":[{'insert_id':insert_id},{'doc_name':{'$regex':doc_name,'$options':'i'}}]}).count():
                faq_data_collection.remove({"$or":[{'insert_id':insert_id},{'doc_name':{'$regex':doc_name,'$options':'i'}}]})
            faq_data_collection.insert_many(faq_data)
        except Exception as e:
            print "\nError in mongo insertion : ", str(e)

    def add_variations(self,text):
        text_to_add = ''
        for each in self.temp_file['data']:
            if SequenceMatcher(None,each['old_text'],text).ratio()>0.99:
                text_to_add = each['new_text']
                print text_to_add
                break

        return text_to_add

    def mergePreviewedFile(self, data): #### insert faq data in mongo

        print "\n merging previewed file : "
        faq_data = []
        doc_name = ''

        if 'filepath' in data and data['filepath']: doc_name = data['filepath']
        elif 'doc_name' in data and data['doc_name']: doc_name = data['doc_name']
        insert_id = int(data['insert_id'])

        #### insert page number in each faq dict
        if 'faq_data' in data and data['faq_data']:
            for dicts in data['faq_data']:
                dicts['insert_id'] = insert_id
                if 'page_no' in dicts: dicts['page_no'] = int(dicts['page_no'])
                if dicts['insert_id'] == int(self.temp_file['insert_id']) and int(data['tenant_id']) == int(self.temp_file['tenant_id']) and int(data['bot_id']) == int(self.temp_file['bot_id']):
                    addTovar = self.add_variations(dicts['text'])
                    dicts['variations'].extend(addTovar)

                faq_data.append(dicts)
        else: faq_data = data['faq_data']
        ####
        #### dump data in Excel faq collection
        if 'excel_faq' in data and data['excel_faq']:
            self.InsertinMongo(data, faq_data, doc_name, insert_id,'faq_excel_data')
        else: self.InsertinMongo(data, faq_data, doc_name, insert_id, 'faq_data')

        if 'faq_data' in data: del data['faq_data']
        if 'json_data' in data: del data['json_data']
        print "\n Inserted faq data in mongo ","=="*25

        ##### create and insert keywords data in mongo
        self.keywordMaker(data)
        # self.createKmStemmedJson(data)

        # ===========Creating disambiguation synonym and acronym =========
        print '===========Creating disambiguation synonym and acronym for one file ========='
        self.disambi_obj.createEachdata(data)


    def insertTableData(self, data,update_flag=''): #### save table json in mongo when we create
        print "in inserting TableData :"

        db_name = data['db_name']
        db = self.mongo_client[db_name]
        table_collection = db['table_data']
        doc_name = ''
        if 'filepath' in data: doc_name = data['filepath']
        elif 'doc_name' in data: doc_name = data['doc_name']

        if update_flag:
            print "in insertTableData for deletion of a pdf table ::"
            if table_collection.find({"$or":[{'insert_id':int(data['insert_id'])},{'doc_name':{'$regex':doc_name,'$options':'i'}}]}).count() > 0:
                table_collection.remove({"$or":[{'insert_id':int(data['insert_id'])},{'doc_name':{'$regex':doc_name,'$options':'i'}}]})
                print "\n documents of repsective file deleted from Mongo ","=="*25

        else:
            print "in insertTableData for updation of a pdf table ::"
            if table_collection.find({"$or":[{'insert_id':int(data['insert_id'])},{'doc_name':{'$regex':doc_name,'$options':'i'}}]}).count() > 0:
                table_collection.remove({"$or":[{'insert_id':int(data['insert_id'])},{'doc_name':{'$regex':doc_name,'$options':'i'}}]})
                print "\n old data deleted from documents deleted from Mongo ","=="*25
            try:
                if 'table_data' in data:
                    tdata = copy.deepcopy(data)
                    table_json = tdata['table_data']
                    for current in table_json:
                        table_collection.insert(current)
                    print "\n html_table_data inserted into mongo ","=="*25
            except Exception as e:
                print "\nError in mongo insertion : ", str(e)


    def keywordMaker(self, data, update_flag = ""):
        try:
            print "\n creating keywords : "
            self.keyword_maker = text_extract()
            self.keyword_maker.Json_Data(data, update_flag = update_flag)
            print "\n Keywords updated !!","=="*25
        except Exception as e:
            print "\nError in Keyword updating : ", str(e)


    def deleteFaqState(self, data):
        try:
            excel_data_updated_flag = False
            model_id = str(data.get("tenant_id", "")) + "_" + str(data.get("bot_id", ""))
            db_name = "db_autobots_" + model_id
            collection_name = "state_merged_data_collection"
            if self.mongo_client[db_name][collection_name].find().count() > 0:
                self.query_create_training_data.main(data.get("tenant_id", ""), data.get("bot_id", ""))
                excel_data_updated_flag = True
            else:
                # if os.path.exists("./faq_state_data/" + model_id):
                shutil.rmtree("./faq_state_data/" + model_id)
        except Exception as e:
            print "\n Error in deleteFaqState : ", traceback.format_exc(), e
        return excel_data_updated_flag

    def hindiCleanQuery(self, query):
        try:
            print "\n inside createLsiWmdCorpus : "
            query_tokens = self.hindi_preprocessor_obj.wordTokenizer(query)
            mod_query = u" ".join(query_tokens)
        except Exception as e:
            print "\n hindiCleanQuery : ", traceback.format_exc(), e
        return mod_query


    def createSearchAnswerList(self, each_language, current_region, current, tokenize_sent):
        sentences_list = []
        variations_list = []
        search_answer_list = []
        if 'text' in current and current['text']:
            if 'region' in current and current_region in current['region']:
                for txt in tokenize_sent:
                    if txt != '':
                        if each_language == "english":
                            txt = self.normalizeMapping(txt)
                            txt = self.cleanQuery(txt)
                        elif each_language == "hindi":
                            txt = self.hindiCleanQuery(txt)
                        if txt and txt not in sentences_list:
                            if len(txt.split()) > 0:
                                sentences_list.append(txt)
                                #### for pulling out matching answer in dic
                                dic = {}
                                dic['text'] = txt
                                dic['my_id'] = current['my_id']
                                dic['user_type'] = "_".join(current['user_type'])
                                dic["language"] = each_language
                                dic["region"] = current_region
                                if 'pdf_faq' in current: dic['pdf_faq'] = True
                                # if current['tag_name'] != 'p': dic['is_heading'] = True
                                # else: dic['is_heading'] = False
                                search_answer_list.append(dic)

        if 'variations' in current and current['variations']:
            if 'region' in current and current_region in current['region']:
                for txt in current['variations']:
                    if txt != '':
                        if each_language == "english":
                            txt = self.normalizeMapping(txt)
                            txt = self.cleanQuery(txt)
                        elif each_language == "hindi":
                            txt = self.hindiCleanQuery(txt)
                        if txt and txt not in sentences_list:
                            if len(txt.split()) > 0:
                                variations_list.append(txt)
                                #### for pulling out matching answer in dic
                                dic = {}
                                dic['text'] = txt
                                dic['my_id'] = current['my_id']
                                dic['user_type'] = "_".join(current['user_type'])
                                dic["language"] = each_language
                                dic['region'] = current_region
                                if 'pdf_faq' in current: dic['pdf_faq'] = True
                                # if current['tag_name'] != 'p': dic['is_heading'] = True
                                # else: dic['is_heading'] = False
                                search_answer_list.append(dic)

        return search_answer_list,sentences_list,variations_list


    def createLsiWmdCorpus(self, data):

        print "\n inside createLsiWmdCorpus : "
        faq_data_list = []
        excel_data_updated_flag = False
        all_language = []
        region_list = []
        try:
            db_name = data['db_name']
            faq_lang_list = []

            faq_data_collection = self.mongo_client[db_name]['faq_data']
            lsi_wmd_corpus_collection = self.mongo_client[db_name]['lsi_wmd_corpus']
            if faq_data_collection.find().count() > 0: all_language = ['english']

            excel_faq_data_collection = self.mongo_client[db_name]['faq_excel_data']
            excel_faq_lsi_wmd_corpus_collection = self.mongo_client[db_name]['faq_excel_lsi_wmd_corpus']
            if excel_faq_data_collection.find().count() > 0:
                faq_lang_list = excel_faq_data_collection.distinct("language")
                all_language.extend(faq_lang_list)
            all_language = list(set(all_language))

            print "\n all_languages : ",all_language

            for each_language in all_language:

                data['current_language'] = each_language

                faq_data_list = []
                if 'pdf_data_updated' in data and data['pdf_data_updated']:
                    faq_data = []
                    if faq_data_collection.find().count() > 0:
                        faq_data = list(faq_data_collection.find({},{'_id':0}))
                        print "\n pdf faq_data : ",len(faq_data)
                        region_list.extend(list(set([region for each in list(faq_data_collection.find({},{'region':1,'_id':0})) for region in each['region']])))
                        pdf_faq_dic = {'pdf_faq':faq_data}
                        faq_data_list.append(pdf_faq_dic)
                    else:
                        data['delete_pdf_model'] = True
                        self.deleteWmdModel(data)

                if 'excel_data_updated' in data and data['excel_data_updated']:
                    excel_faq_data = []
                    if excel_faq_data_collection.find({"language" : each_language}).count() > 0:
                        excel_faq_data = list(excel_faq_data_collection.find({"language" : each_language},{'_id':0}))
                        print "\n excel_faq_data : ",len(excel_faq_data)
                        region_list.extend(list(set([region for each in list(excel_faq_data_collection.find({},{'region':1,'_id':0})) for region in each['region']])))
                        excel_faq_dic = {'excel_faq':excel_faq_data}
                        faq_data_list.append(excel_faq_dic)
                    else:
                        data['delete_excel_model'] = True
                        self.deleteWmdModel(data)
                        excel_data_updated_flag = self.deleteFaqState(data)

                region_list = list(set(region_list))
                print "\n region_list : ",region_list

                for current_region in region_list:

                    data['current_region'] = [current_region]

                    for faq_data_dic in faq_data_list:
                        for faq_data_key,faq_data_val in faq_data_dic.iteritems():
                            if faq_data_val:
                                print "\n faq_data_key ==== ",faq_data_key
                                print "\n combination = ", each_language, current_region, faq_data_key
                                #### remove docs for this language + region from search ans and lsi wmd collections
                                self.deletePrevCorpusSA(faq_data_key, data)
                                #### intialize variables newly
                                search_answer_list = []
                                variations_list = []
                                sentences_list = []

                                for current in faq_data_val:
                                    
                                    tokenize_sent = ''
                                    if 'text' in current and current['text']:
                                        if 'region' in current and current_region in current['region']:
                                            if each_language == "english":tokenize_sent = nltk.sent_tokenize(current['text'])
                                            else:tokenize_sent = [current["text"]]
                                    
                                    # if faq_data_key == 'pdf_faq' or (faq_data_key == 'excel_faq' and current['tag_name'] == 'h2'):        
                                    search_answer_list_t,sentences_list_t,variations_list_t = self.createSearchAnswerList(each_language, current_region, current, tokenize_sent)

                                    search_answer_list.extend(search_answer_list_t)
                                    variations_list.extend(variations_list_t)
                                    sentences_list.extend(sentences_list_t)
                                
                                lsi_wmd_corpus = {'sentences':sentences_list, 'variations':variations_list, 'language':each_language, 'region':current_region}

                                search_answer_final = []
                                search_answer_final =  OrderedDict((frozenset(item.items()),item) for item in search_answer_list).values()

                                if faq_data_key == 'pdf_faq':
                                    data['pdf_faq'] = 1
                                    lsi_wmd_corpus_collection.insert(lsi_wmd_corpus)
                                    search_answer_collection = self.mongo_client[db_name].search_answer_collection

                                if faq_data_key == 'excel_faq':
                                    data['excel_faq'] = 1
                                    excel_faq_lsi_wmd_corpus_collection.insert(lsi_wmd_corpus)
                                    search_answer_collection = self.mongo_client[db_name].faq_excel_search_answer_collection
                                    #### for query decider training
                                    if search_answer_final:
                                        excel_data_updated_flag = True
                                        self.query_create_training_data.main(data['tenant_id'], data['bot_id'])


                                # print "\n search_answer_final == ",search_answer_final
                                if search_answer_final:
                                    search_answer_collection.insert_many(search_answer_final)

                                    #### get focus words for each sentence in data
                                    if each_language == "english":
                                        self.createFocusWords(search_answer_list, sentences_list, data)
                                else: print "\n "

                                if sentences_list or variations_list:
                                    print "\ncall search worker to train lsi wmd models from insert data ====== with ",faq_data_key
                                    self.callSearchWorker(data)
                                if faq_data_key in data: del data[faq_data_key]

            if excel_data_updated_flag:
                self.killProcess()
        except Exception as e:
            print "\nError in createLsiWmdCorpus :::: ", str(e)
            print traceback.format_exc()

    def killProcess(self):
        python_command = "sh kill_faq.sh"
        process = subprocess.Popen(python_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        print "=="*25,"\n process killed successfully : \n","=="*25


    # def createCorpusSAFW(self, data):
    #     print "\n data in createCorpusSAFW : ", json.dumps(data, indent = 4)
    #     lang_reg_file = []
    #     autobots_tenant_data_collection = self.mongo_client[db_name]['clients_data']
    #     lang_reg_file = list(autobots_tenant_data_collection.find({'tenant_id': data['tenant_id'], 'bot_id':data['bot_id'], 'active':True}, {'_id':0, 'language': 1, 'region':1, 'file_type':1}))
    #
    #     faq_data_list = []
    #     if lang_reg_file:
    #         for file_dic in lang_reg_file:
    #             self.deletePrevCorpusSA(file_dic)
    #             faq_data_list.extend(self.collectFaqData(file_dic, data))
    #
    #
    # def collectFaqData(self, file_dic, data):
    #     if file_dic['file_type'].lower() == 'pdf':
    #         faq_data_collection = self.mongo_client[db_name]['faq_data']
    #     elif file_dic['file_type'].lower() == 'faq_excel':
    #         faq_data_collection = self.mongo_client[db_name]['faq_excel_data']
    #     faq_data = []
    #     faq_data = list(pdf_faq_data_collection.find({'region':file_dic['region'], 'language': file_dic['language']},{'_id':0}))
    #     return faq_data


    def deletePrevCorpusSA(self, faq_key, data):
        db_name = data['db_name']
        if faq_key.lower() == 'pdf_faq':
            lsi_wmd_corpus_collection = self.mongo_client[db_name]['lsi_wmd_corpus']
            search_answer_collection = self.mongo_client[db_name]['search_answer_collection']

        elif faq_key.lower() == 'excel_faq':
            lsi_wmd_corpus_collection = self.mongo_client[db_name]['faq_excel_lsi_wmd_corpus']
            search_answer_collection = self.mongo_client[db_name]['faq_excel_search_answer_collection']

        if lsi_wmd_corpus_collection.find({'region':data['current_region'][0],'language':data['current_language']}).count() > 0:
            lsi_wmd_corpus_collection.remove({'region':data['current_region'][0],'language':data['current_language']})
        if search_answer_collection.find({'region':data['current_region'][0],'language':data['current_language']}).count() > 0:
            search_answer_collection.remove({'region':data['current_region'][0],'language':data['current_language']})


    def deleteWmdModel(self, data):
        print "in deleteWmdModel"
        all_files_to_delete = []
        try:
            tenant_id = data.get("tenant_id","")
            bot_id = data.get("bot_id","")
            delete_pdf_model = data.get("delete_pdf_model","")
            delete_excel_model = data.get("delete_excel_model", "")
            model_path = "./data/" + str(tenant_id) + "_" + str(bot_id) + "_trained_models/"
            if delete_pdf_model:
                print "deleted pdfs models"
                pdf_files_name = model_path + "sentences_pdf"
                # if os.path.exists(pdf_files_name):
                all_pdf_models_file = glob(pdf_files_name + "*")
                all_files_to_delete.extend(all_pdf_models_file)
            if delete_excel_model:
                print "deleted excel models"
                excel_files_name = model_path + "sentences_excel"
                # if os.path.exists(excel_files_name):
                all_excel_models_file = glob(excel_files_name + "*")
                all_files_to_delete.extend(all_excel_models_file)
            if all_files_to_delete:
                for each_file in all_files_to_delete:
                    os.remove(each_file)
        except Exception as e:
            print "Error in deleteWmdModel : "  + traceback.format_exc()


    def callSearchWorker(self, data):

        request = {}
        request = data
        request["func_name"] = 'data_for_models'
        print "\n callSearchWorker insert data : training models: ======"
        try:
            job_request = self.gm_client.submit_job("hr_bot_framework_search_worker", json.dumps(request))
        except Exception as e:
            print "\n error in callSearchWorker == ",e
            print traceback.format_exc()

    def createFocusWords(self, search_answer_list, sentences_list, data):

        print "\n creating focus words ==>> "
        focus_word_json = []
        fw_obj = FocusWords()
        focus_words_data = []
        db_name = data['db_name']
        focus_dict = {}

        if 'pdf_faq' in data and data['pdf_faq']:
            focus_word_collection = self.mongo_client[db_name]['focus_words']
        elif 'excel_faq' in data and data['excel_faq']:
            focus_word_collection = self.mongo_client[db_name]['faq_excel_focus_words']

        if focus_word_collection.find({'final':True,'region':data['current_region']}).count() > 0:
            focus_word_collection.remove({'final':True,'region':data['current_region']})

        for dic in search_answer_list:
            if 'text' in dic and dic['text']:
                uni, bi = fw_obj.find_words(dic['text'])
                temp = []

                for wrd in uni:
                    if len(wrd) >= 2:
                        temp.append(wrd)

                temp.extend(bi)
                temp = list(set(temp))

                t = []
                for fw in temp:
                    t.append(fw)
                dic['focus_words'] = tuple(t)
                focus_word_json.append(dic)

        focus_dict['fws'] = focus_word_json
        focus_dict['region'] = data['current_region']
        focus_dict['final'] = True
        print "\n\n len(focus_word_json) == ",len(focus_word_json)
        focus_word_collection.insert(focus_dict)


    def duplicatesRemover(self, seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    def getStopWordsList(self):
        nltk_words = list(stopwords.words('english'))
        not_list = ['not','no','none','nope', 'absent']
        stopWords = [word for word in nltk_words if word not in not_list]
        return stopWords

    def cleanQuery(self, query):
        query = query.lower().strip()
        query = re.sub('<[^<]+?>', ' ', query)
        clean_query = re.sub(r"<\/?ol>|<\/?li>"," ", query)
        clean_query = re.sub(r'[&]', ' and ', clean_query)
        clean_query = re.sub(r'[|]', ' or ', clean_query)
        clean_query = re.sub(r'[^\w]', ' ', clean_query)
        clean_query = clean_query.replace("'","")
        clean_query = clean_query.replace("<br>"," ")
        clean_query = clean_query.replace("</br>"," ")
        clean_query = clean_query.replace("<"," ")
        clean_query = clean_query.replace(">"," ")
        clean_query = clean_query.replace("?"," ")
        clean_query = clean_query.replace("-"," ")
        clean_query = clean_query.replace("."," ")
        clean_query = clean_query.replace(":"," ")
        clean_query = clean_query.replace(")"," ")
        clean_query = clean_query.replace("("," ")
        clean_query = clean_query.replace("*"," ")
        clean_query = clean_query.strip()
        clean_query = re.sub('[\\/\'":]',"",clean_query).encode( "utf-8")
        clean_query = re.sub('[^a-zA-Z0-9\n\.\s]', ' ', clean_query)
        clean_query = re.sub(r'\s+', ' ', clean_query)
        clean_query = clean_query.strip()
        # clean_query = re.sub('[\\/\'":]',"",clean_query).encode( "ascii","ignore")
        return clean_query

    def normalizeMapping(self, query):
        try:
            splited_query = query.split()
            for index, word in enumerate(splited_query):
                word = word.lower()
                if word in self.normalize_mapping:
                    splited_query[index] = self.normalize_mapping[word]
            query = " ".join(splited_query)
        except Exception as e:
            print traceback.format_exc()
        return query

    # def checkLemma(self, wrd):
    #     return nltk.stem.WordNetLemmatizer().lemmatize(wrd, 'v')

    def checkLemma(self, wrd):
        if wrd in self.blockList:
            return wrd
        else:
            return lem(wrd)


    def main(self, data , update_flag = ""):
        print "\n\n insert data main called", json.dumps(data,indent=2)

        #### insert file in faq_data collection
        if update_flag and update_flag == 'update':
            # print "update_flag -->",update_flag, data
            self.keywordMaker(data, update_flag = update_flag)
            # self.createKmStemmedJson(data, update_flag = update_flag)
            self.insertTableData(data,update_flag=update_flag)
            self.disambi_obj.createEachdata(data,update_flag = update_flag)

            self.createLsiWmdCorpus(data)
            # self.query_create_training_data.main(data['tenant_id'], data['bot_id'])

            #TODO : delete tables of the delted file
        else:
            print "\n Added new file: create keywords, focuswords, lsi wmd corpus : "
            self.createFinalKeywords(data)
            # self.createFinalStemmedJson(data)
            self.keymatch_obj.writeIntoSchema(data)
            self.createLsiWmdCorpus(data)


    # def createFinalStemmedJson(self,data):
    #     print "\n In createFinalStemmedJson---->"
    #     try:
    #         if 'pdf_data_updated' in data and data['pdf_data_updated']:
    #             stemmed_json_collection = self.mongo_client[data['db_name']]['stemmed_json']
    #             if stemmed_json_collection.find({'final':True}).count():
    #                 stemmed_json_collection.remove({'final':True})
    #
    #             stem_data = list(stemmed_json_collection.find({},{'_id':0}))
    #             final_stemmed_data = {'final':True,'stemmed_data' : stem_data}
    #             stemmed_json_collection.insert(final_stemmed_data)
    #
    #         if 'excel_data_updated' in data and data['excel_data_updated']:
    #             faq_excel_stemmed_json_collection = self.mongo_client[data['db_name']]['faq_excel_stemmed_json']
    #             if faq_excel_stemmed_json_collection.find({'final':True}).count():
    #                 faq_excel_stemmed_json_collection.remove({'final':True})
    #
    #             stem_data = list(faq_excel_stemmed_json_collection.find({},{'_id':0}))
    #             final_stemmed_data = {'final':True,'stemmed_data' : stem_data}
    #             faq_excel_stemmed_json_collection.insert(final_stemmed_data)
    #
    #     except Exception:
    #         print "Error in createFinalStemmedJson",traceback.format_exc()


    def createFinalKeywords(self, data):
        print "\n In createFinalKeywords ====="
        try:
            db_name = data['db_name']
            keywords_data = []

            # corpus_flag_list = []
            # if 'pdf_data_updated' in data and data['pdf_data_updated']: corpus_flag_list.append('pdf_data_updated')
            # if 'excel_data_updated' in data and data['excel_data_updated']:  corpus_flag_list.append('excel_data_updated')
            #
            # for cf in corpus_flag_list:
            #     if cf == 'pdf_data_updated':keywords_collection = self.mongo_client[db_name]['keywords']
            #     else:faq_excel_keywords_collection = self.mongo_client[db_name]['faq_excel_keywords']
            #
            #     if keywords_collection.find({"final":True}, {'_id':0}).count():
            #         keywords_collection.remove({'final': True})
            #     keywords_data = list(keywords_collection.find({},{'_id':0}))
            #
            #     if keywords_data:
            #         keywords = []
            #         stemmed_keywords = []
            #         final = True
            #         for each_doc in keywords_data:
            #             keywords.extend(each_doc["keywords"])
            #             keywords = list(set(keywords))
            #             stemmed_keywords.extend(each_doc["Stemmed_keywords"])
            #             stemmed_keywords = list(set(stemmed_keywords))
            #
            #         final_data = {"keywords":keywords, "Stemmed_keywords":stemmed_keywords, "final":final}
            #         keywords_collection.insert(final_data)

            if 'pdf_data_updated' in data and data['pdf_data_updated']:

                keywords_collection = self.mongo_client[db_name]['keywords']
                if keywords_collection.find({"final":True}, {'_id':0}).count():
                    keywords_collection.remove({'final': True})

                all_keyword_data = list(keywords_collection.find({'final':False},{'_id':0}))
                regions_list = list(set([region for each in all_keyword_data for region in each['region']]))
                print "\n regions_list pdf : ",regions_list

                for current_region in regions_list:
                    keywords_data = list(keywords_collection.find({'final':False,'region':current_region},{'_id':0}))

                    if keywords_data:
                        keywords = []
                        stemmed_keywords = []
                        final = True
                        for each_doc in keywords_data:
                            keywords.extend(each_doc["keywords"])
                            keywords = list(set(keywords))
                            stemmed_keywords.extend(each_doc["Stemmed_keywords"])
                            stemmed_keywords = list(set(stemmed_keywords))

                        final_data = {"keywords":keywords, "Stemmed_keywords":stemmed_keywords, "final":final,'region':[current_region]}
                        keywords_collection.insert(final_data)
                    else:
                        print "\nNo pdf faq Keyword data found"

            if 'excel_data_updated' in data and data['excel_data_updated']:
                faq_excel_keywords_collection = self.mongo_client[db_name]['faq_excel_keywords']
                if faq_excel_keywords_collection.find({"final":True}, {'_id':0}).count():
                    faq_excel_keywords_collection.remove({'final': True})

                all_keyword_data = list(faq_excel_keywords_collection.find({'final':False},{'_id':0}))
                regions_list = list(set([region for each in all_keyword_data for region in each['region']]))
                print "\n regions_list excel : ",regions_list
                for current_region in regions_list:
                    excel_faq_keywords_data = list(faq_excel_keywords_collection.find({'final':False,'region':current_region},{'_id':0}))

                    if excel_faq_keywords_data:
                        keywords = []
                        stemmed_keywords = []
                        final = True
                        for each_doc in excel_faq_keywords_data:
                            keywords.extend(each_doc["keywords"])
                            keywords = list(set(keywords))
                            stemmed_keywords.extend(each_doc["Stemmed_keywords"])
                            stemmed_keywords = list(set(stemmed_keywords))

                        final_data = {"keywords":keywords, "Stemmed_keywords":stemmed_keywords, "final":final,'region':[current_region]}
                        faq_excel_keywords_collection.insert(final_data)
                    else:
                        print "\nNo excel faq Keyword data found"

        except Exception as e:
            print "Error in createFinalKeywords===> ", traceback.format_exc()



if __name__ == '__main__':
    obj = insertData()
    obj.main()
