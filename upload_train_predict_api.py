# -*- coding: utf-8 -*-

import json
import os
import time
import re
from datetime import datetime
import traceback
import csv
import gensim
from gensim.models.keyedvectors import KeyedVectors
from gensim.similarities import WmdSimilarity

from flasgger import Swagger, swag_from
from flask import Flask, request, jsonify, render_template, flash, redirect
from werkzeug.utils import secure_filename

from excel_bot.excel_worker import ExcelSemanticSimilarity
excel_worker_obj = ExcelSemanticSimilarity()

from pdf_bot.data_maker.pdf_processor import PdfProcessor
pdf_processor_obj = PdfProcessor()

from pdf_bot.qna_worker import AnswerQuestion
qna_worker_obj = AnswerQuestion()

from helper.cleaning_pipeline import Preprocessing
cleaning_pipeline_obj = Preprocessing()

from helper import bert_semantic_search


UPLOAD_FOLDER = 'file_uploads'
if not os.path.exists(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = set(['csv', 'xlsx','pdf', 'docx'])
training_info = json.load(open("training_info.json"))

app = Flask(__name__)
app.debug = True
app.url_map.strict_slashes = False
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/predict')
def home():
	return render_template('home.html')


@app.route('/upload')
def upload_train():
	return render_template('upload_new.html')


@app.route('/upload', methods = ['GET', 'POST'])
def train():
	if request.method == 'POST':
		# check if the post request has the file part
		
		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)

		file = request.files['file']
		required_values = ["model_name", "lang"]
		input_dict = {}
		for key in required_values:
			input_dict[key] = ''
			input_dict[key] = request.values[key]

		now = datetime.now()
		input_dict["model_name"] = "_".join(input_dict["model_name"].split())
		training_info.append({"filename":str(file.filename), "timestamp": str(now), "model_name": input_dict["model_name"]})

		with open("training_info.json", "w+") as fs:
			fs.write(json.dumps(training_info, indent=4))
			print("\n training info written in json successfully !!! ")
		
		if file.filename == '':
			flash('No file selected for uploading')
			return redirect(request.url)

		if file and allowed_file(file.filename):

			filename = secure_filename(file.filename)
			print("\n === ", app.config['UPLOAD_FOLDER'])
			file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			input_dict["file_path"] = file_path
			file.save(file_path)
			flash('File successfully uploaded')

			### decide pdf / excel
			decider(input_dict)
			
			return redirect('/upload')
			# return redirect(request.url)
		else:
			flash('Allowed file types are : csv, xlsx, pdf, docx')
			return redirect(request.url)


def decider(input_dict):
	"""
	this function checks file type and decides whether to train excel bot or pdf bot.
	"""
	if input_dict["file_path"].endswith('pdf') or input_dict["file_path"].endswith('doc') or input_dict["file_path"].endswith('docx'):
		input_dict["model_type"] = "pdf"
		train_pdf(input_dict)

	elif input_dict["file_path"].endswith('xlsx') or input_dict["file_path"].endswith('csv'):
		input_dict["model_type"] = "excel"
		train_excel(input_dict)
		

def train_excel(input_dict):
	"""
	train bot on excel file
	"""
	excel_worker_obj.train(input_dict)


def train_pdf(input_dict):
	"""
	train bot on pdf file
	"""
	#1. extract text
	data_json, solr_json_name, solr_json_path = pdf_processor_obj.main(input_dict["file_path"])
	
	#2. train model
	path = os.path.join(solr_json_path)
	qna_worker_obj.train(path, input_dict["lang"], input_dict["model_type"], input_dict["model_name"])


def read_training_files(bot_base_path, input_dict):
	json_base_path = os.path.join(bot_base_path, input_dict["model_name"], input_dict["lang"], "training_data_jsons")
	training_docs = json.load(open(os.path.join(json_base_path, "sentences_with_id_" + input_dict["model_name"] + ".json")))['sentences']
	id_to_dic = json.load(open(os.path.join(json_base_path, "id_to_dic_" + input_dict["model_name"] + ".json")))
	id_to_ans = json.load(open(os.path.join(json_base_path, "id_to_ans_" + input_dict["model_name"] + ".json")))
	training_sentences = json.load(open(os.path.join(json_base_path, "training_sentences_" + input_dict["model_name"] + ".json")))['sentences']
	return training_sentences, training_docs, id_to_dic, id_to_ans


@app.route('/predict', methods=['POST', 'GET'])
def main():
	try:
		st = time.time()
		required_keys = ['model_type', 'model_name', 'query', 'lang']
		input_dict = {}
		for key in required_keys:
			input_dict[key] = ""
			input_dict[key] = request.values[key]

		orig_query = input_dict["query"]
		input_dict["model_name"] = "_".join(input_dict["model_name"].split())
		
		if not input_dict["model_type"] or not input_dict["lang"] or not input_dict["query"]:
			top_answers = [(0.0, ["Please Enter the all required inputs !!! "])]			
		else:
			print("\n api input --- ", input_dict["query"], input_dict["lang"])

			if input_dict["model_type"] == "pdf":

				# read training files
				bot_base_path = "bots"
				training_sentences, training_docs, id_to_dic, id_to_ans = read_training_files(bot_base_path, input_dict)
				similar_docs = bert_semantic_search.get_similar_questions(input_dict["query"], training_sentences, training_docs)
				similar_docs = [(tpl[0], id_to_ans[str(tpl[1]["my_id"])]) if str(tpl[1]["my_id"]) in id_to_ans else (tpl[0], id_to_dic[str(tpl[1]["my_id"] + 1)]["text"]) for tpl in similar_docs]

				top_answers = similar_docs[:1]
				print("\n top_answers : ", top_answers)
				top_ans_tuple = top_answers


			elif input_dict["model_type"] == "excel":
				bot_base_path = "bots"
				json_base_path = os.path.join(bot_base_path, input_dict["model_name"], input_dict["lang"], "training_data_jsons")
				training_sentences = json.load(open(os.path.join(json_base_path, "training_sentences_" + input_dict["model_name"] + ".json")))['sentences']
				qna_dict = json.load(open(os.path.join(json_base_path, "qna_dict.json")))
				similar_docs = bert_semantic_search.get_similar_questions(input_dict["query"], training_sentences)
				top_answers = similar_docs[:3]
				print("\n top_answer --- ",top_answers)
				if top_answers:
					top_ans = qna_dict[top_answers[0][1]]
					top_ans = top_ans.replace("<p>", "").replace("</p>", "")
					top_ans = top_ans.strip()
					top_ans_tuple = [(top_answers[0][0], top_ans)]
					print("\n top ans === ", top_ans_tuple)
				else:
					top_ans_tuple = [(0.0, "Answer not found!")]

			print("\n total prediction time --- ", time.time() - st)

	except Exception as e:
		print("\n Error in qnamaker API main() --- ", e, "\n ",traceback.format_exc())
		top_ans_tuple = [(0.0, "Something went wrong! please check your inputs and Try again!".upper())]
	return render_template('result.html',query=orig_query, len=len(top_ans_tuple),prediction = top_ans_tuple)


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)