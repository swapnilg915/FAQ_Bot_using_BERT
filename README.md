# FAQ_Bot
Create your own FAQ bot with python and NLP.

It uses googles state of the art (SOTA) model to find the semantic similarity with the FAQ's

steps to create your own FAQBot:

setup the project environment
1. Create virtual environment using the command : python3.7 -m venv faqbot_env_3.7
2. Activate the virtual environment using : source faqbot_env_3.7/bin/activate
3. Run the above command to install setup tools : python3 -m pip install setuptools pip install -U wheel
4. Install all the required python packages using : python3 -m pip install -r requirements.txt
5. Run the flask API : python3 upload_train_predict_api.py
and keep it in any directory and update that path in config.py file. 

Start BERT server:
1. Download pre-trained bert model of your choice from : https://github.com/google-research/bert#pre-trained-models
2. bert-serving-start -model_dir /home/swapnil/Projects/Embeddings/BERT/cased_L-12_H-768_A-12 -num_worker=4

Training:
1. keep your faq data ready in :
	A] xlsx file format with 2 columns namely "Question" and "Answer".
	B] pdf file with a format same as of the file "structured_faq.pdf" in dataset folder.
The sample data used in this project is available in "dataset" folder.
2. In browser run: http://0.0.0.0:5000/upload
3. Provide the necessary inputs like language and model name, select the appropriate path of xlsx / pdf file and click upload.
	Note:Please save the model name somewhere. It will be usefull for prediction.
4. Thats it!!!training is done.

Prediction: 
1. In browser run: http://0.0.0.0:5000/predict
2. Provide the necessary inputs along with a question and hit "Get Answer". You will get an asnwer along with the confidence score.
Thats it!!!


NOTE: The data used for this project is downloaded from microsoft azure website. It is used only for study purpose: https://docs.microsoft.com/en-us/azure/cognitive-services/QnAMaker/concepts/data-sources-and-content

References:
https://github.com/hanxiao/bert-as-service#speech_balloon-faq
https://github.com/hanxiao/bert-as-service/blob/master/example/example8.py


