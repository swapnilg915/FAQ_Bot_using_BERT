import numpy as np
from bert_serving.client import BertClient
from termcolor import colored

topk = 5
questions = []

def get_similar_questions(query, questions, training_docs=[]):
    with BertClient(port=5555, port_out=5556) as bc:
        doc_vecs = bc.encode(questions)
        query_vec = bc.encode([query])[0]
        # compute normalized dot product as score
        score = np.sum(query_vec * doc_vecs, axis=1) / np.linalg.norm(doc_vecs, axis=1)
        topk_idx = np.argsort(score)[::-1][:topk]
        print('top %d questions similar to "%s"' % (topk, colored(query, 'green')))
        if training_docs: similar_questions = [(score[idx], training_docs[idx]) for idx in topk_idx] 
        else: similar_questions = [(score[idx], questions[idx]) for idx in topk_idx] 
        return similar_questions        