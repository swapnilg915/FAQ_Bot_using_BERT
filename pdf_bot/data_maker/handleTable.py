import re
from bs4 import BeautifulSoup , NavigableString
import json
import os
import pprint

class CreateTable(object):
    # generate json for each table in html with structure
                          # [ {
                          #  "col" : [] ,
                          #  "row" :  [] ,
                          #  "table_content" : "" ,
                          #  "parent" : [],
                          #  "table_id" : ""
                          #  } ]

    def __init__(self):
        self.table_dir = "data_maker/table_jsons"

    def createTableJson(self , html_file, html_dict):
        # print("html_file--->",html_file)
        htmlText = html_dict['html_file']

        table_list = []
        table_id = 1
        soup = BeautifulSoup( htmlText , "lxml" )
        table_tag_list = soup.find_all("table") # get all tables of html
        if table_tag_list:
            for table_tag in table_tag_list: # process 1 table at a time
                table_dicti = {"col" : [] ,
                           "row" :  [] ,
                           "table_content" : "" ,
                           "parent" : [],
                           "table_id" : "",
                           "page_no" : "",
                           "insert_id" : 0,
                           "doc_name" : "",
                           }
                # -->> getting parent
                parent_pattern = re.compile(r"b|h[0-9]")
                temp_tag = table_tag
                p_flag = 1
                while p_flag:
                    if temp_tag.find_previous_sibling():
                        if temp_tag.find_previous_sibling().name in [ "h2" , "b" , "h3" , "h4" , "h5" , "h6" ]:
                            table_dicti["parent"].append(temp_tag.find_previous_sibling().name)
                            p_flag = 0
                        else:
                            temp_tag = temp_tag.find_previous_sibling()
                    else:
                        # print("not parent")
                        table_dicti["parent"] = ""
                        p_flag = 0

                # -->> getting id
                table_dicti["table_id"] = "table_" + str(table_id)
                table_id += 1

                # -->> getting table content
                table_dicti["table_content"] = table_dicti["table_content"] + str(table_tag)
                table_dicti["page_no"] = int(table_tag.find_previous('input').get('value'))
                table_dicti['doc_name'] = html_file
                # -->> getting column data
                tr_tag_list =  table_tag.find_all("tr")
                all_td_in_I_tr = tr_tag_list[0].find_all("td")
                for index , td_tag in enumerate(all_td_in_I_tr):
                    if index != 0:
                        refined_text = re.sub(r"\<[a-z0-9]+\>|\<\/[a-z0-9]+\>","",td_tag.text)
                        table_dicti["col"].append(refined_text)

                # -->> getting row data
                for index , tr_tag in enumerate(tr_tag_list):
                    if index != 0:
                        refined_text = re.sub(r"\<[a-z0-9]+\>|\<\/[a-z0-9]+\>","",tr_tag.find("td").text)
                        table_dicti["row"].append(refined_text)
                table_list.append(table_dicti)

        if not os.path.exists(self.table_dir):
                os.makedirs(self.table_dir)

        fname_wo_extension = html_file.rsplit(".")[0]
        json_file_name = self.table_dir + "/tableJson_" + fname_wo_extension + ".json"
        tablejson_name = "/tableJson_" + fname_wo_extension + ".json"
        with open( json_file_name, "w") as f:
            json.dump(table_list, f, indent=2)
        return (table_list,self.table_dir,tablejson_name)

if __name__ == '__main__':
    pass
    # htmlText = ""
    # with open('/home/ishan/edelwise/json2solrjson/solrfiles/Parsley/qwe.html', 'r') as f:
    #     htmlText = f.read()
    # htmlText = re.sub(r"\<\/b\>\s*<b>", " ", htmlText) # merging continious B tags
    # htmlText = re.sub(r'<br>|<hr>', '\n', htmlText) # removing br and hr tags
    # createTableJson(htmlText)
