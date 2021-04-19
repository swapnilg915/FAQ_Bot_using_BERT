import json
import re
import os
import copy
import traceback

class MakeJSON(object):
    
    def __init__(self):
        self.json_dir = "data_maker/json_files/"
        self.final_json_dir = "data_maker/final_json_files/"
        if not os.path.exists(self.final_json_dir):
            os.makedirs(self.final_json_dir)
    
    def makeFinalJson(self , solr_json_list ):
        final_list = []
        # with open(output_fname) as json_f:
        #     json_file = json.load(json_f)
        
        solr_json_copy = copy.deepcopy(solr_json_list)
        final_list = MakeJSON().findJsonParent( "p" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "table" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "b" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "h6" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "h5" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "h4" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "h3" , solr_json_list , final_list , solr_json_copy)
        final_list = MakeJSON().findJsonParent( "h2" , solr_json_list , final_list , solr_json_copy)
        
        # with open("tempFinalJsonTest.json" , "w") as jsonHandle:
        #      json.dump(final_list , jsonHandle , indent = 2)
        
        final_list = MakeJSON().FindOtherParents( "b" , solr_json_list)
        final_list = MakeJSON().FindOtherParents( "h6" , solr_json_list)            
        final_list = MakeJSON().FindOtherParents( "h5" , solr_json_list)            
        final_list = MakeJSON().FindOtherParents( "h4" , solr_json_list)        
        final_list = MakeJSON().FindOtherParents( "h3" , solr_json_list)            
        final_list = MakeJSON().FindOtherParents( "h2" , solr_json_list)
        
        return final_list


    def FindOtherParents(self , tag_name , solr_json_list ):
        final_list = []
        new_final_list = []
        check_in_read_list = 1
        check_in_solr_json = 1
        with open("data_maker/tempFinalJson.json" , "r") as jsonHandle:
            final_list = json.load( jsonHandle )

        for index , tag in enumerate(final_list):
            if tag["tag_name"] == tag_name:
                if tag["parent"]:
                        if len(new_final_list) > 0:
                            for new_tag in new_final_list:
                                if new_tag["my_id"] == tag["parent"][0]:
                                    new_tag["all_childs"].append(tag)
                                    check_in_read_list = 0
                                    break
                                else:
                                    check_in_read_list = 1
                        if len(final_list) > 0:
                            if check_in_read_list == 1:
                                for this_tag in final_list:
                                    if this_tag["my_id"] == tag["parent"][0]:
                                        this_tag["all_childs"].append(tag)
                                        new_final_list.append(this_tag)
                                        check_in_solr_json = 0
                                        break
                                    else:
                                        check_in_solr_json = 1
                            else:
                                check_in_solr_json = 0
                        if len(solr_json_list) > 0:
                            if check_in_solr_json == 1:
                                for parent_tag in solr_json_list:
                                    if parent_tag["my_id"] == tag["parent"][0]:
                                        parent_tag["all_childs"].append(tag)
                                        new_final_list.append(parent_tag)
                                        check_in_solr_json = 0
                                        break
                                    else:
                                        "no parent found in solr json"
                            else:
                                pass
                else:
                     new_final_list.append(tag)
            else:
                new_final_list.append(tag)
                
        with open("data_maker/tempFinalJson.json" , "w") as jsonHandle:
            json.dump(new_final_list , jsonHandle , indent = 2)
        return new_final_list
            
    
    def findJsonParent( self , tag_name , json_file , final_list , solr_json_copy):
        for index , tag in enumerate(json_file):
            if tag["tag_name"] == tag_name or tag["tag_name"][:len(tag["tag_name"])-2] == tag_name:
                
                if tag["tag_name"] == "b":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                elif tag["tag_name"] == "h6":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                elif tag["tag_name"] == "h5":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                elif tag["tag_name"] == "h4":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                elif tag["tag_name"] == "h3":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                elif tag["tag_name"] == "h2":
                    if tag["childs"]:
                        pass
                    else:
                        final_list.append(tag)
                else:
                    if tag["parent"]:
                        temp_dicti = {}
                        check_in_PCjson = 1
                        if len(final_list) >= 1:
                            for tagFL in final_list:
                                if tagFL["my_id"] == tag["parent"][0]:
                                    tagFL["all_childs"].append(tag)
                                    check_in_PCjson = 0
                                    for index , del_tagFL in enumerate(final_list):
                                        if del_tagFL["my_id"] == tag["my_id"]:
                                            del final_list[index]
                                    break
                                else:
                                    check_in_PCjson = 1
                        if check_in_PCjson == 1:
                             for tagPC in solr_json_copy:
                                if tagPC["my_id"]  == tag["parent"][0]:
                                    temp_dicti = tagPC
                                    temp_dicti["all_childs"].append(tag)
                                    final_list.append(temp_dicti)
                                    for index , del_tag in enumerate(final_list):
                                        if del_tag["my_id"] == tag["my_id"]:
                                            del final_list[index]
                                    break
                    else:
                        if tag["child"]:
                            final_list.append(tag)
                        else:
                            final_list.append(tag)
        with open("data_maker/tempFinalJson.json" , "w") as jsonHandle:
            json.dump(final_list , jsonHandle , indent = 2)
        return final_list
    
    
    def makeJSON(self, intermidiate_list ,url):
        solr_json_list = []
        sorted_json = []
        htmlJSON_list = []
        htmlJSON_list = intermidiate_list
        
        try:
            sorted_json = tuple(sorted(htmlJSON_list, key= lambda x: x['my_id']))
            for ind, each in enumerate(sorted_json):
                current_tag = each['tag_name']
                curr_id = each['my_id']
                each['childs'] = self.findChilds(sorted_json[ind+1:], current_tag)
                each['parent'] = self.findParent(sorted_json[:ind], current_tag)
                solr_json_list.append(each)
    
            ######### create solr json
            if not os.path.exists(self.json_dir):
                os.makedirs(self.json_dir)
            only_fname = url.rsplit("/")[-1]
            fname_wo_extension = only_fname.rsplit(".")[0]
            solr_file_name = "solrJson_" + fname_wo_extension + ".json"
            solr_file_path = self.json_dir + solr_file_name
            with open(solr_file_path, "w") as f:
                json.dump(solr_json_list, f , indent = 2)
            
            ######### create final json (with all_childs)
            final_json = MakeJSON().makeFinalJson(solr_json_list)
            final_json_name = "finalJson_" + fname_wo_extension + ".json"
            final_json_path = self.final_json_dir + final_json_name
            
            with open(final_json_path, "w") as f:
                json.dump(final_json, f , indent = 2)
                
        except Exception as e:
            print("\n Error in json2solrJSON => makeJSON :: ",e,"\n",traceback.format_exc())
        
        return solr_json_list, solr_file_name, solr_file_path

    def findChilds(self, child_list, current_tag):
        main_child_list = []
        child_h_tag = []
        immidiate_child = ""
        immidiate_child_flag = 1
        direct_p_t_flag = 1
        child_h_flag = 0
        break_child_h_no = 0
        if current_tag == 'p': # for p tags
            return []
        elif current_tag.startswith('t'): # for t tags
            return []
        else: 
            if current_tag.startswith("h"): # for h tags
                heading_number = int(current_tag[-1])
                if child_list:
                    for each in child_list:
                        if child_h_flag == 0:
                            if each['tag_name'].startswith('h') and (int(each['tag_name'][-1]) > heading_number):
                                main_child_list.append(each['my_id'])
                                child_h_tag.append(each["tag_name"])
                                break_child_h_no = int(each['tag_name'][-1])
                                immidiate_child_flag = 0
                                child_h_flag = 1
                            elif each['tag_name'].startswith('h') and (int(each['tag_name'][-1]) <= heading_number):
                                immidiate_child_flag = 0
                                break
                            # elif each['tag_name'] == immidiate_child:
                            #     main_child_list.append(each['my_id'])
                            if immidiate_child_flag == 1: # if p,b or t tags are immidiate to h tag, add as child of h, else not
                                if each['tag_name'].startswith('b'):
                                    main_child_list.append(each['my_id'])
                                    immidiate_child = each['tag_name']
                                    direct_p_t_flag = 0
                                elif each['tag_name'].startswith('p'):
                                    if direct_p_t_flag == 1:
                                        main_child_list.append(each['my_id'])
                                        immidiate_child = each['tag_name']
                                else:  # else startswith('t'):
                                    if direct_p_t_flag == 1:
                                        main_child_list.append(each['my_id'])
                                        immidiate_child = each['tag_name']
                        else:
                            if each['tag_name'].startswith("h"):
                                if int(each['tag_name'][-1]) < break_child_h_no:
                                    break
                                elif each['tag_name'] == child_h_tag[0]:
                                    main_child_list.append(each['my_id'])
                                else:
                                    pass
                return main_child_list
            else: # for b tags
                if child_list:
                    for each in child_list:
                        if each['tag_name'] == 'p':
                            main_child_list.append(each['my_id'])
                        elif each['tag_name'].startswith('t'):
                            main_child_list.append(each['my_id'])
                        else:
                            break
                return main_child_list


    def findParent(self, parent_list, current_tag):
        main_parent_list = []
        if current_tag.startswith("h"):
            if parent_list:
                for each in reversed(parent_list):
                    if each["tag_name"].startswith("h"):
                        if int(each["tag_name"][-1]) > int(current_tag[-1]):
                            continue
                        elif int(each["tag_name"][-1]) < int(current_tag[-1]):
                            main_parent_list.append(each["my_id"])
                            break
                        else:
                            pass
        elif current_tag.startswith("b"):
            if parent_list:
                for each in reversed(parent_list):
                    if each["tag_name"].startswith("h"):
                        main_parent_list.append(each["my_id"])
                        break
                    else:
                        continue
        elif current_tag.startswith("p"): # or current_tag.startswith("t"):
            found = 0
            if parent_list:
                for each in reversed(parent_list):
                    if each["tag_name"].startswith("h") or each["tag_name"].startswith("b"):
                        main_parent_list.append(each["my_id"])
                        found = 1
                        break
                    else:
                        continue
                if found == 0:
                    main_parent_list.append(0)
            else:
                main_parent_list.append(0)
                
        elif current_tag.startswith("t"):
            found = 0
            if parent_list:
                for each in reversed(parent_list):
                    if each["tag_name"].startswith("h") or each["tag_name"].startswith("b"):
                        main_parent_list.append(each["my_id"])
                        found = 1
                        break
                    else:
                        continue
                if found == 0:
                    main_parent_list.append(0)
            else:
                main_parent_list.append(0)
        return main_parent_list


if __name__ == '__main__':
    pass
