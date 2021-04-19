# -*- coding: utf-8 -*-

import json
import os
import time
import re
import traceback
import fasttext
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

# from flair.embeddings import FlairEmbeddings, BertEmbeddings, XLNetEmbeddings, XLMEmbeddings, StackedEmbeddings
# bert_embedding = BertEmbeddings('bert-base-multilingual-cased')
# flair_forward_embedding = FlairEmbeddings('multi-forward')
# flair_backward_embedding = FlairEmbeddings('multi-backward')
# xl_embedding = XLNetEmbeddings()

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

	def cleaning_pipeline(self, text, lang):
		text = self.clean_text(text)
		text = self.get_lemma(text, lang)
		return text


	def create_dict(self, row):
		return {"Conversation_id":row["Conversation Id"], "text":row["Intent Text"], "intent":row["Intent"], "response":row["Intent Response"]}


	def read_data(self):
		df = pd.read_excel("data/happybytes_faq.xlsx")
		sentences = list(df["Question"])
		self.documents = sentences		
		return sentences

	
	def load_word2vec(self, lang):
		st = time.time()
		# self.model = Word2Vec.load('20_newsgroup_word2vec.model')
		fasttext_path = "../word2vec_models/fasttext_300_" + lang + ".bin"
		self.model = gensim.models.keyedvectors.Word2VecKeyedVectors.load_word2vec_format(fasttext_path, binary=False)
		# self.model = KeyedVectors.load_word2vec_format('/home/swapnil/Downloads/Embeddings/GoogleNews-vectors-negative300.bin.gz', limit=300000, binary=True)
		print("\n time to load the fasttext model --- ", time.time() - st)

	def load_fasttext(self, lang):
		st = time.time()
		fasttext_path = ""
		self.model = fasttext.load_model(fasttext_path)
		print("\n time to load the fasttext model --- ", time.time() - st)


	def train(self, lang):
		st = time.time()
		sentences = self.read_data()

		with open("training_jsons/training_sentences_nb_happybytes_faq.json", "w+") as fs:
			fs.write(json.dumps({"sentences":sentences}, indent=4))

		sentences = [ self.cleaning_pipeline(sent, lang) for sent in sentences]

		sentences = [ word_tokenize(sent) for sent in sentences]

		self.load_word2vec(lang)

		train_time = time.time()
		instance_wmd = WmdSimilarity(sentences, self.model)
		instance_wmd.save("models/fasttext_wmd_nb_happybytes_faq.model")
		del self.model
		print("\n wmd training time --- ",time.time()-train_time)
		print("\n total execution time --- ",time.time() - st)


	def test(self, query, lang, model):
		st = time.time()
		query = self.cleaning_pipeline(query, lang)
		print("\n query --- ",query)
		query_token = word_tokenize(query)
		print("\n query_token --- ",query_token)
		load_time = time.time()

		instance_wmd = gensim.similarities.docsim.Similarity.load('nb_happybytes_faktura_faq_fasttext_wmd.model')
		training_sentences = json.load(open("training_sentences_nb_happybytes_faktura_faq.json"))['sentences']

		print("\n time to load model --- ", time.time() - load_time)
		wmd_sims = instance_wmd[query_token]
		
		wmd_sims = sorted(enumerate(wmd_sims), key=lambda item: -item[1])
		similar_docs = [(s, training_sentences[i])  for i,s in wmd_sims]
		similar_docs = similar_docs[:3]
		print("similar docs --- ")
		for tpl in similar_docs:
			print(tpl)
		# for tpl in similar_docs:
		# 	print(tpl)
		print("\n total prediction time --- ", time.time() - st)

	def check_word(self, word, lang):
		self.load_word2vec(lang)
		print("\n word --- ",word," --- ", self.model[word])

if __name__ == '__main__':
	obj = ExcelSemanticSimilarity()

	# lang = "en"
	# model = "qnamaker_faq"

	lang = "nb"
	model = "happybytes_faq"

	# obj.train(lang)


	### febdok pred test
	# febdok_variations = ["is there phone support for febdok ?", "is it necessary to download integrator program", "is there any site to download software", "currency rate", "what are the opening hours for integrator support", "how to login to the febdok"]
	# obj.test("how to login to the febdok", lang)
	# obj.check_word("harassment", lang)

	### ask ubuntu pred test
	# variations = ["how to convert pdf to docx", "how to read a qr code", "suggest me a good pdf viewer", "suggest me php editor", "shortcut to shutdown", "how to upgrade from ubuntu 14 to 15?"]
	# obj.test("how to adjust screen brightness" , lang, model)

	### qnamaker faq sample
	# var = ["is this service free", "can i integrate this service on my website", "procedure to login", "steps to login", "steps to log in to a portal", "how big a knowledge base can be?"]
	# query = "is this service free"
	# obj.test(query , lang, model)

	### happybytes_faktura sample

	### orig query = Kommer faktura på e-post eller brev? = Will an invoice come by e-mail or letter?
	# hvordan faktura kommer til å komme = how invoice is going to come
	# vil en faktura komme med et innlegg = will an invoice come by a post
	# "er faktura som kommer via en e-post" = is invoice coming by an email
	
	### orig query = Kan dere forklare beløpet jeg fikk på min første faktura? = Can you explain the amount I received on my first invoice?
	# "kan du forklare beløpet på fakturaen" = can you explain the amount of the invoice
	# Jeg trenger detaljering av beløp på faktura = i need detailing of amount on invoice
	
	### orig query = Kan jeg betale fakturaen fra dere med Vipps? = Can I pay your invoice with Vipps?
	# hvordan kan jeg betale fakturaen din = how can i pay your invoice
	# hva er måtene å betale fakturabeløpet på? = what are the ways to pay the invoice amount
	
	### orig query = Hvor kan jeg se hvilke fakturaer som er betalt? = Where can I see which invoices have been paid?
	# hvordan du sjekker den betalte fakturaen = how to check the paid invoice
	# hvor jeg kan sjekke de betalte fakturaene = where i can check the paid invoices

	var  = ["hvordan faktura kommer til å komme", "vil en faktura komme med et innlegg", "er faktura som kommer via en e-post", "kan du forklare beløpet på fakturaen", "Jeg trenger detaljering av beløp på faktura", "hvordan kan jeg betale fakturaen din", "hva er måtene å betale fakturabeløpet på?", "hvor jeg kan sjekke de betalte fakturaene"]

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