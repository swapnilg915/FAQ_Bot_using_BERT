import regex as re
import json
import os

from spacy.lang.en import English
spacy_en = English(disable=['parser', 'ner'])
from spacy.lang.nb import Norwegian
spacy_nb = Norwegian(disable=['parser', 'ner'])

from spacy.lang.en.stop_words import STOP_WORDS as stopwords_en
from spacy.lang.nb.stop_words import STOP_WORDS as stopwords_nb

stopwords_en = list(stopwords_en)
stopwords_nb = list(stopwords_nb)

mapping_dict = {"en":[stopwords_en, spacy_en], "nb":[stopwords_nb, spacy_nb]} 

class Preprocessing(object):

	def __init__(self):
		pass

	def clean_text(self, text):
		try:
			text = str(text)
			text = re.sub(r"[^a-zA-ZÅÆÄÖØÜåæäöøüß]", " ", text)
			text = re.sub(r"\s+", " ", text)
			text = text.lower().strip()
		except Exception as e:
			print("\n Error in clean_text : ", e,"\n",traceback.format_exc())
		return text

	def get_lemma(self, text, lang):
		return " ".join([tok.lemma_.lower().strip() for tok in mapping_dict[lang][1](text) if tok.lemma_ != '-PRON-' and tok.lemma_ not in mapping_dict[lang][0]])

	def get_lemma_tokens(self, text, lang):
		return [tok.lemma_.lower().strip() for tok in mapping_dict[lang][1](text) if tok.lemma_ != '-PRON-' and tok.lemma_ not in mapping_dict[lang][0]]

	def cleaning_pipeline(self, input_dict):
		text = self.clean_text(input_dict['query'])
		text = self.get_lemma_tokens(text, input_dict['lang'])
		return text


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
