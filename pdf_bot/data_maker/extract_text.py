from __future__ import print_function
import os
import re
import sys
import pdfplumber
import pandas as pd
import traceback
# from html5lib import html5parser
import pprint
from bs4 import BeautifulSoup,NavigableString,Tag
from unidecode import unidecode
import itertools
import difflib

class PdfPlumb(object):
    def __init__(self):
        #self.fname = self.check_train_fname(fname)
        # self.fname = "/home/swapnil/projects/claimslink_dev/invoiceReader/datasets/template_wise_invoices/fjordkraft/Faktura_Fjordkraft.pdf"
        self.fname = "/home/swapnil/projects/claimslink_dev/invoiceReader/datasets/template_wise_invoices/activ/Faktura 130041.pdf"
        self.output_dir = "outputs"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.debug = 1
        self.html_str = ""


    def getHTML(self, fname):
        self.html_str = ""
        self.pdfReadable = True
        self.fname = fname
        only_fname = self.fname.rsplit("/")[-1]
        fname_wo_extension = only_fname.rsplit(".")[0]
        self.output_fname = self.output_dir + "/" + fname_wo_extension + ".html"
        self.html_str += "<html><head><title>" + fname_wo_extension + "</title></head><body>"
        pd.set_option('display.max_colwidth', -1)

        html = ''
        self.fname = self.check_train_fname(fname)
        if self.fname == "@@error@@":print ("\n file name not present")
        else:html = self.extract_html()
        if not self.pdfReadable: html = ''
        return html, self.pdfReadable


    def check_train_fname(self, fname):
        extn = fname.rsplit(".")
        if os.path.isfile(fname) and extn and extn[-1].lower() == "pdf":
            return fname
        else:
            print ("\n  File not found...\n  Enter 'pdf' path to extract: ")
            return "@@error@@"


    def table_rule(self, table):
        filtered_table = filter(lambda row_: row_, list(map(lambda row_:[cell for cell in row_ if cell], table)))
        rule = not all(map(lambda row: len(row) == 1, filtered_table))

        if rule:
            len_rows =  list(map(lambda row: len(row), table))
            avg_rows = sum(len_rows)/len(len_rows)
            rule = all(map(lambda rowlen : bool(rowlen/avg_rows), len_rows))
        return rule

    def save_table(self, table):
        #we can save the table info as per our need
        dframe_table = pd.DataFrame(table)
        # html_table = dframe_table.to_html(header = False, index = False,classes=['table-responsive'])
        html_table = dframe_table.to_html(header = False, index = False,classes=['table','table-bordered']).replace('border="1"','border="0"')
        if self.debug:print("html_table --> \n", html_table, end="\n\n")
        return html_table

    def remove_table(self, page_extract, table):
        page_extract = page_extract.strip()
        str_lines = page_extract.splitlines()
        str_lines = [i for i in str_lines if i.isspace()==False]
        #pprint.pprint(str_lines)
        match_inlines = lambda cells: [l_ for cell in cells for l_, line in enumerate(str_lines) if cell in line]

        filtered_table = filter(lambda row_: row_, list(map(lambda row_:[cell for cell in row_ if cell], table)))
        matched_cell = map(lambda row_: [match_inlines(cell.split("\n")) for cell in row_], filtered_table)
        #print("all_rows", filtered_table, end="\n\n")
        #print("matched_cell", matched_cell, end="\n\n")
        # for lin_ind, lines in enumerate(str_lines):
            #print("lines", lin_ind, lines)
        #raw_input("***" * 20)

        wospacelines = [re.sub(r"(<[\/]?b>)|(<[\/]?h[1-6]>)", "", line.replace(" ", "")) for line in str_lines]
        matches_found = [[] for l in range(len(wospacelines))]
        def match_all_inlines(filtered_table):
            for row in filtered_table:
                for cells in row:
                    for l_ind_, line in enumerate(wospacelines):
                        for cell in cells.split("\n"):
                            for find_ in re.finditer(re.escape(re.sub(r"(<[\/]?b>)|(<[\/]?h[1-6]>)", "", cell.replace(" ", ""))), line):
                                matches_found[l_ind_].extend(range(find_.start(), find_.end()))
        match_all_inlines(filtered_table)
        matches_found = [list(set(line_)) for line_ in matches_found]
        remove_lines = [line_ for line_, (line, orig_line) in enumerate(zip(matches_found, wospacelines)) if len(line) == len(orig_line) and len(line) != 0 ]
        #print("remove_lines", remove_lines, end="\n\n")

        sequences = [[]]
        old_seq_val, seq_ind = 0, 0
        for seq_val in sorted(set(remove_lines),key=lambda x:remove_lines.index(x)):
            if old_seq_val and (old_seq_val + 1 != seq_val):
                seq_ind += 1
                sequences.append([])
            old_seq_val = seq_val
            sequences[seq_ind].append(seq_val)
        sequence_len = [len(sequence) for sequence in sequences]
        #print("sequences", sequences, end="\n\n")
        #print("sequence_len", sequence_len, end="\n\n")
        max_seq_length = max(sequence_len)
        #print("max_seq_length", max_seq_length, end="\n\n")
        table_remove_lines = [sequence for seqlen, sequence in zip(sequence_len, sequences) if len(sequence) == max_seq_length]
        #print("table_html", table_remove_lines, end="\n\n")

        #raw_input("***" * 20)
        for row in table:
            for cell in row:
                if cell is None:
                    table[table.index(row)][row.index(cell)] = ' '

        table_html_format = self.save_table(table)

        #raw_input("***" * 20)

        str_lines2 = [i for i in page_extract.splitlines() if i.isspace()==False]
        table_remove_lines2 = []

        if len(table_remove_lines)>=1:
            for l1 in table_remove_lines:
                for l2 in l1:
                    table_remove_lines2.append(l2)

        #b.set_trace()
        for lin_ind, lines in enumerate(str_lines):
            if lin_ind in table_remove_lines2:

                lines = ""
                str_lines2[lin_ind] = ""
            #print("lines", lin_ind, lines)
        #raw_input("***" * 20)



        if table_remove_lines2:
            str_lines2[table_remove_lines2[0]]=''.join(table_html_format)
        #print("page after placing the table --> \n")
        # for lin_ind, lines in enumerate(str_lines2):
            #print("lines", lin_ind, lines)
        #raw_input("+++" * 20)
        page_extract = "\n".join(str_lines2)
        return page_extract

    def format_page_extract(self, page_extract):
        page_lines = [l.strip() for l in page_extract.splitlines()]

        start_regex = r"^((<b>)|(<h[1-6]>))"
        end_regex = r"((<[\/]b>)|(<[\/]h[1-6]>))\s*$"
        regex_group_1 = r"<(b|h[1-6])>"
        regex_group_2 = r"</(b|h[1-6])>"
        new_page_lines = []
        old_line, tag_name = "", ""

        # page_lines = ['<li>' + line + '</li>' for line in page_lines if line.startswith('')]

        for line in page_lines:
            start_matches = list(re.finditer(start_regex, line, re.MULTILINE))
            end_matches = list(re.finditer(end_regex, line, re.MULTILINE))
            if not old_line:
                if line:
                    if len(start_matches) == 0: #start has b or h[1-6] tag not present
                        if line[-1] not in ['.', '?', '!', ':']:
                            tag_name = "p"
                            old_line = '<' + tag_name + '>' + line
                        else:
                            new_page_lines.append('<p>' + line + '</p>')
                    else:
                        if len(end_matches) == 0:
                            search_group_1 = re.findall(regex_group_1, line)
                            search_group_2 = re.findall(regex_group_2, line)
                            if len(search_group_1) == len(search_group_2):
                                tag_name = 'p'
                                # old_line = '<' + tag_name + '>' + line
                                search_group_2_iter = re.finditer(regex_group_2, line)
                                for match in search_group_2_iter:
                                    start = match.span()[0]
                                    end = match.span()[1]
                                    break
                                temp_line = line[:end] + '<'+tag_name+'>' +line[end:]
                                old_line = temp_line
                            else:
                                regex_group = r"^<(b|h[1-6])>"
                                search_group = re.search(regex_group, line)
                                tag_name = search_group.groups()[0]
                                old_line = line
                        else:
                            new_page_lines.append(line) #start as well as end has b or h[1-6] tag
                else:
                    new_page_lines.append(line) #blank line append
            else:
                if line:
                    if line.find('</' + tag_name + '>') != -1:
                        if line.endswith('</' + tag_name + '>'):
                            new_page_lines.append(old_line + " " + line)
                            old_line, tag_name = "", ""
                        else:
                            new_page_lines.append('<p>' + old_line + " " + line + '</p>')
                            old_line, tag_name = "", ""
                    else:
                        if len(start_matches) == 0:
                            if line[-1] in ['.', '?', '!', ':']:
                                new_page_lines.append(old_line + " " + line + '</' + tag_name + '>')
                                old_line, tag_name = "", ""
                            else:
                                old_line += " " + line
                        else:
                            new_page_lines.append(old_line + '</' + tag_name + '>')
                            search_group_1 = re.findall(regex_group_1, line)
                            search_group_2 = re.findall(regex_group_2, line)
                            if len(search_group_1) == len(search_group_2):
                                tag_name = 'p'
                                # old_line = '<' + tag_name + '>' + line
                                search_group_2_iter = re.finditer(regex_group_2, line)
                                for match in search_group_2_iter:
                                    start = match.span()[0]
                                    end = match.span()[1]
                                    break
                                temp_line = line[:end] + '<'+tag_name+'>' +line[end:] + '</'+tag_name+'>'
                                line = temp_line
                            new_page_lines.append(line)
                            old_line, tag_name = "", ""
                else:
                    new_page_lines.append(old_line + '</' + tag_name + '>')
                    old_line, tag_name = "", ""
                    new_page_lines.append(line)
        if old_line:
            new_page_lines.append(old_line +'\n'+ '</' + tag_name + '>')

        def lines_check(line):
            if re.sub(r"(<[\/]?b>)|(<[\/]?h[1-6]>)", "", line.replace(" ", "")) != "":
                return True
            return False
        page_extract_lines = [line for line in new_page_lines]
        page_extract = "\n".join(page_extract_lines)
        return page_extract

    def remove_footer(self, footer_text, page_extract_list):
        for foo in footer_text:
            foo = re.sub(r'\s','',foo)
            for line in page_extract_list:
                temp_line = re.sub(r'\s', '', line)
                if foo == temp_line:
                    return line
        return ''

    def find_header_footer(self, pages, option = 'footer'):
        end_of_page = []
        page_extract = ''
        index_footer = []

        for ind_, page in enumerate(pages):
            try:
                end_of_page.append(page.last_line(option))
            except Exception:
                print("\n Error in find_header_footer 1 == ",traceback.format_exc())
                self.pdfReadable = False
                self.html_str += "<hr>"

        footer_text = []
        if self.pdfReadable:
            for ind_, page in enumerate(pages):
                for top in end_of_page[ind_]:
                    try:
                        got_text = page.text_last_line(top)
                        # footer_text.append(page.text_last_line(top))
                        # got_text = [foo for foo in footer_text if re.search(r'[\w]+', foo)]
                        if re.search(r'\w', got_text):
                            footer_text.append(got_text)
                            break
                    except:
                        print("\n Error in find_header_footer 2 == ",traceback.format_exc())
                        self.html_str += "<hr>"

        index_footer = []
        for a, b in itertools.combinations(range(len(footer_text)), 2):
            if difflib.SequenceMatcher(None, footer_text[a], footer_text[b]).ratio() > 0.95:
                index_footer.append(footer_text[a])
                index_footer.append(footer_text[b])
        index_footer = list(set(index_footer))
        return index_footer


    def extract_html(self):

        self.pdfReadable = True
        pdf = pdfplumber.open(self.fname)
        pages = pdf.pages
        if self.debug:print("\n\nTotal pages:", len(pages), end="\n")
        headers = {}
        footers = {}
        page_footer = []
        page_footer = []
        for ind_, page in enumerate(pages):
            try:
                if self.pdfReadable == True:
                    page_extract = page.extract_text()

                    if page_extract != None:
                        page_number = '<input type="hidden" id="page_no_' + str(ind_ + 1) + '" value="'+ str(ind_ + 1) + '">'
                        # page_extract = '<input type="text" class="page_number" id="'+ str(ind_) + '" value="'+ str(ind_) +'" style="visibility:hidden">'
                        table_extract = page.extract_tables()
                        print("\n table_extract : ", table_extract)
                        page_extract_list = page_extract.split('\n')
                        rem_line = ''
                        if page_footer:
                            rem_line = self.remove_footer(page_footer, page_extract_list)
                        if rem_line:
                            page_extract_list.remove(rem_line)
                        page_extract = '\n'.join(page_extract_list)

                        ##### swapnilg => to remove headers and footers
                        # if len(pages) > 1:
                        #     pattern = re.search(r"(?<=\<\w\>)(\w.*?)(?=\<\/\w\>)",page_extract,re.MULTILINE | re.IGNORECASE)
                        #     if pattern:
                        #         headers[ind_] = pattern.group(0)
                        #     page_extract_list = page_extract.split('\n')
                        #     page_extract_list = [ txt.strip() for txt in page_extract_list if txt and txt!='' and bool(txt.strip())]
                        #     if page_extract_list: footers[ind_] = page_extract_list[-1]
                        # ####

                        if page_extract:
                            str_lines = page_extract.splitlines()

                        if table_extract:
                            for table in table_extract:
                                is_table = self.table_rule(table)
                                if is_table:
                                    # self.save_table(table)
                                    if page_extract:
                                        page_extract = self.remove_table(page_extract, table)

                        if page_extract:
                            page_extract = self.format_page_extract(page_extract)
                            page_extract = self.headersCheck(page_extract,str(ind_ + 1))
                        str_lines = page_extract.splitlines()

                        if page_extract:
                            self.html_str += page_number + page_extract
                            self.html_str += "<hr>"
                    else:
                        raise Exception('None')
                else:
                    print("\n pdfReadable False :::: ")

            except Exception as e:
                if str(e) == 'None':
                    print("Raised Exception PDF could not be extracted : PDF Not readable using PDFplumber")
                else:
                    print("\n Error in extract_html == ",traceback.format_exc())
                    self.html_str += "<hr>"
                self.pdfReadable = False

        self.html_str += "</body></html>"
        return self.html_str


    def headersCheck(self,page_extract,page_no):
        soup = BeautifulSoup(page_extract,'html.parser')
        for i in soup.find_all('p',text=True):
            pass
        return page_extract

    def write_html(self):
        with open(self.output_fname, "w") as f_w:
            try:
                f_w.write(self.html_str.replace("\n", "<br>"))
            except:
                f_w.write(self.html_str.encode('utf-8').replace("\n", "<br>"))
        #print("\n  Output: " + str(self.output_fname), end="\n")

if __name__ == '__main__':
    # pass
    # fname = ""
    # if len(sys.argv) > 1:
    #     fname = sys.argv[1]
    
    obj = PdfPlumb()
    # obj.extract_html()
    # obj.write_html()

    obj.extract_html()
