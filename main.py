from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
from pathlib import Path
from io import StringIO
import re
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

# NOTES
# - keep in mind, this script works if every line in the file has the '€' symbol in the 'Últ. Precio'
#   column. In some cases (either they forgot, or their script failed) the '€' symbol does not appear,.
#   and causes the parser to break.
#   If this happens, just run the first method, comment it out, then modify the file and add the '€'
#   where it's missing, and run the second method.

# TODO
# - right now I'm only retrieving last values (Últ.valor) because it was the easiest.
#   I can retrieve all the other values just by taking into account that decimal values are
#   represented with two digits after the comma.

# Maybe I can build a huge-ass regular expression to parse this by lines...

class Value():
    """
    Represents a Value with its ISIN code, last price, change since last month,
    change since three months, YTD, change since last year, change since five years, 
    div. yld %
    """

    def __init__(self, isin:str='None', last_price:str='0,00', one_month:str='0,00', three_months:str='0,00', ytd:str='0,00', last_year:str='0,00', yld:str='0,00'):
        """
        Class instance. Default values are strings.
        """
        self.isin = isin
        self.last_price = last_price
        self.one_month = one_month
        self.three_months = three_months
        self.ytd = ytd
        self.last_year = last_year
        self.yld = yld

class SingularBankParser():
    """
    Class for parsing data from SingularBank values basket.
    """
    

    def __init__(self):
        """
        Class instance.
        """
        self.PDF_HEADER = ''
        # self.PDF_LINE = re.compile('[A-Z][A-Z](([0-9]|[A-Z]){10}) (-?[0-9],([0-9]{2}){6})')
        self.VALUE_CODE_GENERAL = re.compile('[A-Z][A-Z](([0-9]|[A-Z]){10})[0-9]+,([0-9]+){2}') # value code
        self.VALUE_CODE_SPECIFIC = re.compile('[A-Z][A-Z](([0-9]|[A-Z]){10})') # value code
        self.LAST_PRICE = re.compile('[0-9]+,[0-9]+') # last price info
        self.VALUE_DATA = re.compile('(-)?[0-9]+,([0-9]){2}') # data from the value code

        # self.values_dict = {} # dict containing the values
        self.values_list = []

    def process_list_of_values(self, values_list: list):
        """
        Processes list of items containing values and monetary values.
        Values are fixed-length 12 chars long strings representing the value name.
        They have two capital letters at the begginning and the rest are 10 digits.
        """
        last_value = None

        for item in values_list:
            item = item.strip()
            print(f'item->{item}')

            if len(item) > 1:
                # get the value code:
                value_code = ''
                value_price = ''


                data_value_match = re.search(self.VALUE_DATA, item)
                if data_value_match is not None:
                    # check if it has been a false positive:
                    false_positive = True if re.match(self.VALUE_CODE_GENERAL, item) is not None else False
                    if not false_positive:
                        print(f'data in the item={item}')
                        one_month = re.search(self.VALUE_DATA, item).group(0)
                        item = item.replace(one_month, '')
                        three_months = re.search(self.VALUE_DATA, item).group(0)
                        item = item.replace(three_months, '')
                        ytd = re.search(self.VALUE_DATA, item).group(0)
                        item = item.replace(ytd, '')
                        last_year = re.search(self.VALUE_DATA, item).group(0)
                        item = item.replace(last_year, '')
                        yld = re.search(self.VALUE_DATA, item).group(0)

                        last_value.one_month = one_month
                        last_value.three_months = three_months
                        last_value.ytd = ytd
                        last_value.last_year = last_year
                        last_value.yld = yld

                        # add to the list of values
                        self.values_list.append(last_value)


                value_code_match = re.search(self.VALUE_CODE_GENERAL, item)
                if value_code_match is not None:
                    match_object = value_code_match.group(0)
                    print(f'match_object={match_object}')
                    value_code = re.search(self.VALUE_CODE_SPECIFIC, match_object).group(0)
                    match_object = match_object.replace(value_code, '')
                    value_price = re.search(self.LAST_PRICE, match_object).group(0)
                    item = item.replace(value_code, '') # remove the value
                    value_price = re.search(self.LAST_PRICE, match_object).group(0)
                    item = item.replace(value_price, '') # remove the price 
                    print(f'value_code={value_code}')
                    print(f'value_price={value_price} EUR')

                    value = Value(isin=value_code, last_price=value_price)

                    last_value = value
                    print(f'last_value now has an object={last_value}')
                    print(f'item after processing codes={item}')
        # finished iterating through data. Print list
        for p_value in self.values_list:
            print(f'code->{p_value.isin}')
            print(f'last_price->{p_value.last_price}')
            print(f'one_month->{p_value.one_month}')
            print(f'three_months->{p_value.three_months}')
            print(f'ytd->{p_value.ytd}')
            print(f'last_year->{p_value.last_year}')
            print(f'yld->{p_value.yld}')
            


    def parse_pdf(self, documents_path: Path, output_path: Path):
        """
        Main method for parsing the PDF. Uses the PDFMiner API
        to parse the data straight from the PDF.

        Parameters
        ----------
        documents_path:Path
            Path to the document.
        output_path:Path
            Path for the output txt file.
        """
        output_string = StringIO()

        with open(documents_path, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            for page in PDFPage.create_pages(doc):
                interpreter.process_page(page)

        read_text = output_string.getvalue()

    # write input to txt file
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(read_text)

    def process_data(self, output_path: Path):
        """
        Processes data from the text parsed from a PDF file.
        """
        with open(output_path, 'r', encoding='utf-8') as infile:
            # read text and split the codes and prices

            for line in infile:
                # self.process_list_of_values2(line)
                # print(f'line={line}')
                if '€' in line:
                    self.process_list_of_values(line.split('€'))


def main():
    """
    Runs the main program. Reads from a file.
    """
    documents_path = Path(
        f'cesta-mercado-europeo.pdf')
    output_path = Path(f'cesta-mercado-europeo.txt')
    # output_path = Path(f'cestesta.txt')
    singular_bank_parser = SingularBankParser()
    # singular_bank_parser.parse_pdf(documents_path)
    singular_bank_parser.process_data(output_path)


if __name__ == '__main__':
    main()
