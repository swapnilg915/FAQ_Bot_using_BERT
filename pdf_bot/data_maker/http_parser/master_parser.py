from urllib.request import Request, urlopen
from http_parser.response_parser import ResponseParser
from http_parser.page_parser import PageParser
from tools.general import *
import json
import re

def removeBr(url):
    with open(re.sub(r'file://','',url), 'r') as f:
        html = f.read()
    html = re.sub(r'<br>|<hr>', '\n', html)
    with open(re.sub(r'file://','',url), 'w') as f:
        f.write(html)

class MasterParser:

    @staticmethod
    # def parse(url, output_dir, output_file):
    def parse(url):
        print('Crawling ' + url)
        removeBr(url)
        resp = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}))
        resp_bytes = resp.read()
        print("12121212121221",resp_bytes)
        print(type(resp_bytes))
        resp_parser = ResponseParser(resp)
        print("3434343434343434343434343434",resp_parser)
        try:
            page_parser = PageParser(resp_bytes.decode('utf-8'))
            print("5656565656565656",page_parser)
        except UnicodeDecodeError:
            return
        json_results = {
            'url': url,
            'status': resp.getcode(),
            'headers': resp_parser.headers,
            'tags': page_parser.all_tags
        }
        # write_json(output_dir + '/' + output_file + '.json', json_results)
        # print ("-*-*-*-*-**-\n",json.dumps(json_results))
        return json_results
