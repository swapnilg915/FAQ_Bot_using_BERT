import traceback
import json
from data_maker.pdf_processor import PdfProcessor

class PdfParser(object):

	def __init__(self):
		self.pdf_processor = PdfProcessor()

	def main(self, path):
		try:
			data_json = self.pdf_processor.main(path)
			# print("\n data json --- ", json.dumps(data_json, indent=4))
		except Exception as e:
			print("\n Error in pdfPlumberExtractor --- ",e,"\n ",traceback.format_exc())
			pass

if __name__ == "__main__":
	obj = PdfParser()
	path = "/home/swapnil/projects/fretex_pdf_parser/sf-ocr/data/travel_data/Avklaring_søknad_1.pdf"
	obj.main(path)