import traceback
import json
import re
import os
import time
import pickle
import unicodedata
from collections import defaultdict

from spacy.lang.en import English
spacy_en = English(disable=['parser', 'ner'])

from spacy.lang.en.stop_words import STOP_WORDS as stopwords_en

stopwords_en = list(stopwords_en)

mapping_dict = {"en":[stopwords_en, spacy_en]}

import config as cf


class AnswerQuestion(object):

	def __init__(self):
		pass


	def creat_ans(self, dic, id_to_dic):
		final_ans = ""

		if dic["tag_name"] == "b" and dic["childs"]:
			for child_id in dic["childs"]:
				final_ans += id_to_dic[child_id]["text"]
		elif dic["tag_name"] == "b" and not dic["childs"]:
			final_ans += dic["text"]
		elif dic["tag_name"] == "p" and dic["parent"] and dic["parent"] != [0]:
			parent_id = dic["parent"][0]
			parent_dic = id_to_dic[parent_id]
			for child_id in parent_dic["childs"]:
				final_ans += id_to_dic[child_id]["text"]

		# elif dic["tag_name"] == "p" and dic["parent"] and dic["parent"] == [0]:

		return re.sub(r"\s+", " ",final_ans)


	def create_and_save_answers(self, sentences_with_id, id_to_dic):
		id_to_ans = defaultdict()
		for dic in sentences_with_id:
			ans = self.creat_ans(dic, id_to_dic)
			if ans:id_to_ans[dic["my_id"]] = [ans]
		
		with open(self.ans_file_name, "w+") as fs:
			fs.write(json.dumps(id_to_ans, indent=4))
		

	def sentence_adder(self, dic):
		self.train_sents.append(dic["text"])
		return dic


	def make_dir(self, path):
		if not os.path.exists(path):
			os.makedirs(path)
			print("\n directory created for path : ",path)


	def create_bot_structure(self, path, lang, model_name, model_type):
		bot_base_path = "bots"
		self.make_dir(bot_base_path)
		self.make_dir(os.path.join(bot_base_path, model_name))
		self.make_dir(os.path.join(bot_base_path, model_name, lang))
		self.trained_models_dir = os.path.join(bot_base_path, model_name, lang, "trained_models")
		self.make_dir(self.trained_models_dir)
		self.traininig_data_dir = os.path.join(bot_base_path, model_name, lang, "training_data_jsons")
		self.make_dir(self.traininig_data_dir)
		self.extracted_html_dir = os.path.join(bot_base_path, model_name, lang, "extracted_html_jsons")
		self.make_dir(self.extracted_html_dir)
		self.ans_file_name = os.path.join(self.traininig_data_dir, "id_to_ans_" + model_name + ".json")
		self.sentences_file_name = os.path.join(self.traininig_data_dir, "sentences_with_id_" + model_name + ".json")
		self.dic_file_name = os.path.join(self.traininig_data_dir, "id_to_dic_" + model_name + ".json")
		print("\n created directory structure ::: ")


	def read_data(self, lang, model_name, path):
		json_data = json.load(open(path))

		id_to_dic = defaultdict()
		for dic in json_data:
			id_to_dic[dic["my_id"]] = dic

		self.train_sents = []

		""" for all tags """
		sentences_with_id = [self.sentence_adder(val_dict) for key, val_dict in id_to_dic.items()]

		with open(self.sentences_file_name, "w+") as fs:
			fs.write(json.dumps({"sentences":sentences_with_id}, indent=4))
			print("\n training sentences written successfully in json!")

		with open(self.dic_file_name, "w+") as fs:
			fs.write(json.dumps(id_to_dic, indent=4))
			print("\n id_to_dic written successfully in json!")

		self.create_and_save_answers(sentences_with_id, id_to_dic)
		return self.train_sents


	def train(self, path, lang, model_type, model_name):
		st=time.time()
		self.create_bot_structure(path, lang, model_name, model_type)
		training_sentences = self.read_data(lang, model_name, path)
		with open(os.path.join(self.traininig_data_dir, "training_sentences_" + model_name + ".json"), "w+") as fs:
			fs.write(json.dumps({"sentences":training_sentences}, indent=4))


if __name__ == "__main__":
	obj = AnswerQuestion()
	lang = "nb"
	obj.train(lang)

	while True:
		query = input("\nEnter the question : ")
		if query == "exit": break
		obj.test(query, lang)
		print("==="*30)


