# -*- coding: utf-8 -*-

import json
import os
import time
import re
import traceback
import csv
import pandas as pd
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import gensim
from gensim.models.keyedvectors import KeyedVectors
from gensim.similarities import WmdSimilarity

from flasgger import Swagger, swag_from
from flask import Flask, request, jsonify, render_template

from spacy.lang.en import English
spacy_en = English(disable=['parser', 'ner'])
from spacy.lang.nb import Norwegian
spacy_nb = Norwegian(disable=['parser', 'ner'])

from spacy.lang.en.stop_words import STOP_WORDS as stopwords_en
from spacy.lang.nb.stop_words import STOP_WORDS as stopwords_nb

stopwords_en = list(stopwords_en)
stopwords_nb = list(stopwords_nb)

mapping_dict = {"en":[stopwords_en, spacy_en], "nb":[stopwords_nb, spacy_nb]}

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('home.html')


class SemanticSimilarity(object):

	def __init__(self):
		pass


	def clean_text(self, text):
		try:
			text = str(text)
			text = re.sub(r"[^a-zA-ZÅÆÄÖØÜåæäöøüß]", " ", text)
			text = re.sub(r"\s+", " ", text)
			text = text.lower().strip()
		except Exception as e:
			print("\n Error in clean_text --- ", e,"\n ", traceback.format_exc())
			print("\n Error sent --- ", text)
		return text

	def get_lemma(self, text, lang):
		return " ".join([tok.lemma_.lower().strip() for tok in mapping_dict[lang][1](text) if tok.lemma_ != '-PRON-' and tok.lemma_ not in mapping_dict[lang][0]])

	def cleaning_pipeline(self, text, lang):
		text = self.clean_text(text)
		text = self.get_lemma(text, lang)
		return text

obj = SemanticSimilarity()


@app.route('/get_similar_question', methods=['POST', 'GET'])
def main():
	st = time.time()
	# query = request.args.get("query")
	# lang = request.args.get("lang")

	query = request.form['query']
	lang = request.form['lang']

	print("\n api input --- ", query, lang)
	query = obj.cleaning_pipeline(query, lang)
	query_token = word_tokenize(query)
	print("\n query_token --- ",query_token)
	load_time = time.time()

	if lang == "en":
		instance_wmd = gensim.similarities.docsim.Similarity.load('en_febdok_fasttext_wmd.model')
		training_sentences = json.load(open("febdok_training_sentences_en.json"))['sentences']
	else:
		instance_wmd = gensim.similarities.docsim.Similarity.load('nb_nelfo_fasttext_wmd.model')
		training_sentences = json.load(open("nelfo_training_sentences.json"))['sentences']
	
	print("\n time to load model --- ", time.time() - load_time)
	wmd_sims = instance_wmd[query_token]
	
	wmd_sims = sorted(enumerate(wmd_sims), key=lambda item: -item[1])
	similar_docs = [(s, training_sentences[i])  for i,s in wmd_sims]
	top_answers = similar_docs[:5]
	print("top_answers --- ", top_answers)
	# for tpl in similar_docs:
	# 	print(tpl)
	# top_answers = [tpl[1] for tpl in similar_docs]
	print("\n top_answer --- ",top_answers )
	print("\n total prediction time --- ", time.time() - st)

	return render_template('result.html',query=query, len=len(top_answers),prediction = top_answers)


if __name__ == '__main__':
	app.run(debug=True)