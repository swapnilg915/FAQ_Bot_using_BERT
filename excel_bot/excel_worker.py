# -*- coding: utf-8 -*-

import json
import os
import time
import re
import traceback
import pandas as pd

from flasgger import Swagger, swag_from
from flask import Flask, request, jsonify, render_template

from spacy.lang.en import English
spacy_en = English(disable=['parser', 'ner'])

from spacy.lang.en.stop_words import STOP_WORDS as stopwords_en
stopwords_en = list(stopwords_en)
mapping_dict = {"en":[stopwords_en, spacy_en]}

import config as cf

app = Flask(__name__)
app.debug = True
app.url_map.strict_slashes = False
Swagger(app)


class ExcelSemanticSimilarity(object):

	def __init__(self):
		pass


	def clean_text(self, text):
		try:
			text = str(text)
			text = re.sub(r"[^a-zA-Z0-9ÅÆÄÖØÜåæäöøüß.]", " ", text)
			text = re.sub(r"\s+", " ", text)
			text = text.lower().strip()
		except Exception as e:
			print("\n Error in clean_text --- ", e,"\n ", traceback.format_exc())
			print("\n Error sent --- ", text)
		return text

	def get_lemma(self, text, lang):
		return " ".join([tok.lemma_.lower().strip() for tok in mapping_dict[lang][1](text) if tok.lemma_ != '-PRON-' and tok.lemma_ not in mapping_dict[lang][0]])

	def get_lemma_tokens(self, text, lang):
		return [tok.lemma_.lower().strip() for tok in mapping_dict[lang][1](text) if tok.lemma_ != '-PRON-' and tok.lemma_ not in mapping_dict[lang][0]]

	def cleaning_pipeline(self, text, lang):
		text = self.clean_text(text)
		text = self.get_lemma_tokens(text, lang)
		return text


	def create_dict(self, row):
		return {"Conversation_id":row["Conversation Id"], "text":row["Intent Text"], "intent":row["Intent"], "response":row["Intent Response"]}


	def read_data(self, path):
		df = pd.read_excel(path)
		sentences = list(df["Question"])
		qna_dict = {ques:ans for ques, ans in zip(list(df["Question"]), list(df["Answer"]))}
		self.documents = sentences		
		return sentences, qna_dict

	
	def load_word2vec(self, lang):
		st = time.time()
		self.model = KeyedVectors.load_word2vec_format(cf.word2vec_model_path, limit=100000, binary=True)
		print("\n time to load the word2vec model --- ", time.time() - st)


	def make_dir(self, path):
		if not os.path.exists(path):
			os.makedirs(path)
			print("\n directory created for path : ",path)


	def create_bot_structure(self, input_dict):
		bot_base_path = "bots"
		# self.make_dir(bot_base_path)
		# self.make_dir(os.path.join(bot_base_path, input_dict["model_name"]))
		self.make_dir(os.path.join(bot_base_path, input_dict["model_name"], input_dict["lang"]))
		self.trained_models_dir = os.path.join(bot_base_path, input_dict["model_name"], input_dict["lang"], "trained_models")
		self.make_dir(self.trained_models_dir)
		self.traininig_data_dir = os.path.join(bot_base_path, input_dict["model_name"], input_dict["lang"], "training_data_jsons")
		self.make_dir(self.traininig_data_dir)
		print("\n created directory structure ::: ")


	def train(self, input_dict):
		st = time.time()
		self.create_bot_structure(input_dict)
		sentences, qna_dict = self.read_data(input_dict["file_path"])

		with open(os.path.join(self.traininig_data_dir, "qna_dict.json"), "w+") as fs:
			fs.write(json.dumps(qna_dict, indent=4))
			print("\n qna_dict written successfully!!!")

		with open(os.path.join(self.traininig_data_dir, "training_sentences_" + input_dict["model_name"] + ".json"), "w+") as fs:
			fs.write(json.dumps({"sentences":sentences}, indent=4))


if __name__ == '__main__':
	obj = ExcelSemanticSimilarity()

	lang = "en"
	model = "qnamaker_faq"
	obj.train(lang)
	var  = ["Who is the target audience for the QnA Maker tool?", "How do I log in to the QnA Maker Portal?", "Is the QnA Maker Service free?", "My URLs have valid FAQ content, but the tool cannot extract them. Why not?", "What format does the tool expect the file content to be?", "How large a knowledge base can I create?", "Do I need to use Bot Framework in order to use QnA Maker?", "Where is the test web-chat URL from the old portal? How do I share my KB with others now?", "How do I embed the QnA Maker service on my website?"]
	while True:
		query = input("\nEnter the question : ")
		if query == "exit": break
		obj.test(query , lang, model)
		print("==="*30)



""" TODO
1. spell checker
2. remove headers and footers
3. Norwegian model
4. integrate FLASK UI

"""