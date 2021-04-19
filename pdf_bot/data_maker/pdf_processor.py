# pylint: disable=all
import sys, traceback, random, os, urllib, json, subprocess, shutil
import datetime
import bs4
import regex as re
from copy import deepcopy
# from HTMLParser import HTMLParser
from html.parser import HTMLParser
from bs4 import BeautifulSoup, NavigableString, Tag

import pprint
from pdf_bot.data_maker.extract_text import PdfPlumb
from pdf_bot.data_maker.handleTable import CreateTable
from pdf_bot.data_maker.json2solrJSON import MakeJSON
# from urllib.request import Request, urlopen
from pdf_bot.data_maker.http_parser.response_parser import ResponseParser
from pdf_bot.data_maker.http_parser.page_parser import PageParser
from pdf_bot.data_maker.tools.general import *


class PdfProcessor(object):
    def __init__(self):
        self.pdfPlumb = PdfPlumb()
        self.makeJson = MakeJSON()
        self.createTable = CreateTable()
        self.html_files_path = 'data_maker/html_files/'
        
        self.path_to_read_from = "./"
        self.directory = "data_maker/json_files"
        self.table_directory = "data_maker/table_jsons"
        # print("\nworking...")
        self.debug=0

    def main(self, file_path):
        data_json = {}
        try:
            if file_path.endswith('docx') or file_path.endswith('doc'):
                subprocess.call(["doc2pdf", file_path])
                file_path = file_path.replace('.docx','.pdf')
                file_path = file_path.replace('.doc','.pdf')

            data_json, solr_json_name, solr_json_path = self.pdfToHtml(file_path)
            # print("\n successfully extracted PDF --- ", data_json)

        except Exception as e:
            print("\n Error in decider ==>> ",e,"\n",traceback.format_exc())
        return data_json, solr_json_name, solr_json_path

    def pdfToHtml(self, path):
        data_json = {}
        html_text, pdfReadable = self.pdfPlumb.getHTML(path)
        if pdfReadable:
            html_file, html_dict = self.writeHTMLToFile(html_text)
            data_json, table_json, solr_json_name, solr_json_path = self.htmlToJson(html_dict, html_file)
        return data_json, solr_json_name, solr_json_path


    def createPreviewJson(self, html_file, html_dict):
        html_file_content = ''
        # if os.path.isfile(html_path):
        #     html_file_content = urllib.urlopen(html_path).read()
        html_file_content = html_dict['html_file']
        re_html = re.sub(r'(<input id=\"page_no_.*?\"/?>)', '$$$', html_file_content)
        re_html = re_html.split('$$$')
        re_html = [sent.replace('\n','').strip() for sent in re_html]
        html_json = []
        for ind in range(1, len(re_html)):
            html_json.append({'page_number':ind, 'html':re_html[ind]})
        preview_html_json = {'file_name':html_file,'pdf_title':re_html[0], 'data':html_json}
        return preview_html_json


    def htmlToJson(self, html_dict, html_file):
        #### STEP 2: convert html to raw json
        url = self.html_files_path + html_file
        intermidiate_dict = self.parse(url, html_dict)
        intermidiate_dict = self.makeIntermediateJSONFormat(html_file, intermidiate_dict)
        with open("data_maker/withIdJson.json" , "w") as jsonHandle:
            json.dump(intermidiate_dict , jsonHandle , indent = 2)
        #### STEP 3: create final json from raw json
        solr_json, solr_json_name, solr_json_path = self.makeJson.makeJSON(intermidiate_dict ,url)

        #### create tables json
        table_json, table_json_path, table_json_name = self.createTable.createTableJson(html_file, html_dict)
        table_json = self.tableIDinSequence(solr_json,table_json)
        if not os.path.exists('data_maker/'+table_json_path):
            os.makedirs('data_maker/'+table_json_path)
        json.dump(table_json,open(table_json_path+'/'+table_json_name,'w'),indent=4)

        #### move html file
        src_path = 'data_maker/new_html_files/' + html_file
        dest_path = 'data_maker/processed_html/' + html_file
        if not os.path.exists('data_maker/processed_html'):
            os.makedirs('data_maker/processed_html')
        # shutil.move(src_path, dest_path)
        return solr_json, table_json, solr_json_name, solr_json_path
            

    def parse(self, url, html_dict):
        # print('\nCrawling ' + url)
        # print("\n html_dict --- ",html_dict)
        resp_bytes = ''
        json_results = {}
        try:
            resp_bytes = html_dict['html_file']
            resp_bytes = resp_bytes.replace('<strong>','&lt;b&gt;')
            resp_bytes = resp_bytes.replace('</strong>','&lt;/b&gt;')
            resp_bytes = resp_bytes.replace('<table','<p>.</p><table')
            page_parser = PageParser(resp_bytes)
            json_results = {
                'url': url,
                'status': 200,
                'headers': {},
                'tags': page_parser.all_tags
            }

            # print("\n json_results --- ",json_results)
            with open("data_maker/temp.json","w") as dict_handle:
                json.dump(json_results , dict_handle, indent = 2)

        except Exception:
            print('Error in parse() PdfProcessor-->',traceback.format_exc())
        return json_results

    def tableIDinSequence(self,faq_json, table_json):
        faq_data_list = []
        a_counter = 0
        for i in faq_json:
            i.pop('all_childs')
            if i['tag_name'] == 'table':
                a_counter +=1
            faq_data_list.append(i)

        if self.debug:print("\n tables in table_json : ",len(table_json))
        if self.debug:print("\n tables in faq_json : ", a_counter)

        counter = 0
        for dictn in faq_data_list:
            if dictn['tag_name'] == 'table':
                if self.debug:print("TABLE ID : ", dictn['table_id'])
                if self.debug:print("lst : ",dictn['table_id'].split('_'))
                if self.debug:print("counter : ",counter)
                table_json[counter]['table_id'] = int(dictn['table_id'].split('_')[-1])
                counter = counter + 1
        return table_json


    def makeIntermediateJSONFormat(self, doc_name, intermidiate_dict, start_point=1):
        my_id = 1
        #table_json = self.createTable.createTableJson(html_file, my_id)
        table_id = 1
        html_list = []
        td_flag = 1
        
        for tag in intermidiate_dict["tags"]:
            if tag['attributes']:
                if 'value' in tag['attributes'] and tag['attributes']['value']:
                    page_number = tag['attributes']['value']
            if tag['content']:
                if tag['name'] == 'title':
                    continue
                elif tag['name'] == 'td' or tag['name'] == 'tr' or tag['name'] == 'th':
                    if td_flag:
                        temp = {}
                        temp['my_id'] = my_id
                        temp['childs'] = []
                        temp['parent'] = []
                        temp['text'] = ""
                        temp['tag_name'] = "table"
                        temp['doc_name']  = doc_name
                        temp['table_id'] = "table_" + str(my_id)
                        temp["all_childs"] = []
                        # temp["page_no"] = page_number
                        html_list.append(temp)
                        table_id += 1
                        my_id += 1
                        td_flag = 0
                else:
                    temp = {}
                    temp['my_id'] = my_id
                    temp['childs'] = []
                    temp['parent'] = []
                    temp['text'] = tag['content']
                    temp['tag_name'] = tag['name']
                    temp['doc_name']  = doc_name
                    temp['table_id'] = ""
                    temp["all_childs"] = []
                    # temp["page_no"] = page_number
                    html_list.append(temp)
                    my_id += 1
                    td_flag = 1

        return html_list


    def writeHTMLToFile(self, html_text):
        soup = ''
        if not os.path.exists("data_maker/html_files/"):
            os.makedirs("data_maker/html_files/")
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        file_name = now + ".html"
        html_text = re.sub(r"\<\/b\>\s*<b>", " ", html_text) # merging continious B tags
        html_text = re.sub(r'<br>|<hr>', '\n', html_text) # removing br and hr tags
        soup = BeautifulSoup(html_text, 'html.parser') # html5lib, lxml, html.parser

        all_p = soup.find_all("p")
        for p in all_p:
            for tag in p.findAll(True):
                if tag.name == "b":
                    s = ""
                    for c in tag.contents:
                        if not isinstance(c, NavigableString):
                            c = strip_tags(str(c), invalid_tags)
                        s += str(c)
                    tag.replaceWith(s)
        html_dict = {}
        region = []
        try:
            # html_text = self.htmlparser.unescape(str(soup))
            html_dict = {'file_name':file_name,'html_file':str(soup)}
        except Exception:
            print("\n writeHTMLToFile --- ",traceback.format_exc())
        return file_name, html_dict


    def change_wrong_p_tags(self,soup):
        new_html = ""
        head_tag = str(soup.find('head'))
        body_tag = soup.find('body')
        tag_class = bs4.element.Tag
        string_class = bs4.element.NavigableString
        try:
            for ind, tag in enumerate(body_tag.findChildren()):
                if type(tag) is bs4.element.Tag:

                    if tag.name == 'p':
                        found = 0
                        if tag.text:
                            para_tokens = tag.text.split()
                            if para_tokens and (para_tokens[0].isupper() or re.search(r'^(\d{1,}.)',tag.text)) and (not re.search(r'([.]{4,})',tag.text)):
                                match = re.search(r'^([A-Z /]+)[a-z]',tag.text)
                                if match:
                                    new_b = match.group(1).split()[:-1]
                                    new_p = match.group(1).split()[-1] + str(re.sub(r'(^[A-Z ]+)',"",tag.text))
                                    new_b = " ".join(new_b)
                                    if len(str(new_b))>1: new_html += "\n" + "<b>" + str(new_b) + "</b>"
                                    new_html += "\n" + "<p>" + str(new_p) + "</p>"
                                    found = 1
                                if not found:
                                    match2 = re.search(r'^([A-Z ,-/)(]+)',tag.text)
                                    if match2:
                                        new_html = self.changeOnlyCapsTags(match2,new_html,tag,1)
                                        found = 1
                                if not found:
                                    match3 = re.search(r'^(\d{1,}\.[A-Z ,-/)(]+)',tag.text)
                                    if match3:
                                        new_html = self.changeOnlyCapsTags(match3,new_html,tag,1)
                                        found = 1
                                if not found:
                                    new_html += "\n" + str(tag)
                            else:
                                new_html += "\n" + str(tag)
                        else:
                            pass
                    else:
                        if tag.name.startswith('t'):
                            pass
                        else:
                            new_html += "\n" + str(tag)
                elif type(child) is bs4.element.NavigableString:
                    new_html += "\n" + str(tag)
            final_html = "<html>" + head_tag + new_html + "</html>"
            return BeautifulSoup(final_html,'html.parser')
        except Exception as e:
            print("\n change_wrong_p_tags --- ",traceback.format_exc())
            return soup

    def changeOnlyCapsTags(self,match,new_html,tag,digit_flag):
        if digit_flag:
            lower_case_match = re.search(r'[a-z]+',tag.text)
            if not lower_case_match:
                new_b = match.group(1)
                if len(str(new_b))>1: new_html += "\n" + "<b>" + str(new_b) + "</b>"
            else:
                new_html += "\n" + "<p>" + str(tag.text) + "</p>"
        else:
            new_b = match.group(1)
            if len(str(new_b))>1: new_html += "\n" + "<b>" + str(new_b) + "</b>"
        return new_html

if __name__ == '__main__':
    print('\nprocessing pdf and dumping data in database:')
    obj = PdfProcessor()
    path = "/home/swapnil/data_folder/Projects/github/FAQ_Bot/dataset/structured_faq.pdf"
    obj.main(path)
