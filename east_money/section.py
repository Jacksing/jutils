# encoding='utf-8'

# pylint: disable=c0111,c0325

import json
import logging
import re
from urllib import urlencode

import requests


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


def get_sections():
    # We can get the list of all sections in notion page or area page or trade page.
    #   http://quote.eastmoney.com/center/BKList.html#notion
    #   http://quote.eastmoney.com/center/BKList.html#area
    #   http://quote.eastmoney.com/center/BKList.html#trade
    # Here we do this through notion page.
    notion_url = 'http://quote.eastmoney.com/center/BKList.html#notion'
    page = requests.get(notion_url)
    page.encoding = 'gbk'
    html = page.text

    section_list = re.findall(
        r'a href="list\.html#(\d{8})_\d_\d"><span class="text">(.+?)</span>',
        html
    )

    return {
        'area': [section for section in section_list if section[0].startswith('28001')],
        'trade': [section for section in section_list if section[0].startswith('28002')],
        'notion': [section for section in section_list if section[0].startswith('28003')],
    }

def get_stock_list_of_section(cmd_code, section_name):
    url = 'http://nufm.dfcfw.com/EM_Finance2014NumericApplication/JS.aspx?'
    query = {
        'type': 'CT',
        'sty': 'FCOIATA',
        'sortType': 'A',  # sort by stock code
        'sortRule': '',  # sort ascending
        'page': '1',
        'pageSize': '2000',
        'token': '7bc05d0d4c3c22ef9fca8c2a912d779c',
        'js': '[(x)]',
        'cmd': cmd_code,
    }
    resp = requests.get(url + urlencode(query))
    if resp.status_code != 200:
        logger.error('get_stock_list_of_section error')
    result = resp.json()
    logger.info('-> got %s stocks for section %s', str(len(result)).rjust(5), section_name)
    return result

stock_section_info_cache = None

def get_stock_section_info():
    global stock_section_info_cache
    stock_dict = {}
    section_dict = get_sections()

    def _get_section_info(stock_list, section_category='others'):
        for stock in stock_list:
            stock_code, stock_name = stock.split(',')[1:3]
            if stock_code not in stock_dict:
                stock_dict[stock_code] = {
                    'name': stock_name,
                    section_category: [section_name],
                }
            else:
                if stock_dict[stock_code]['name'] != stock_name:
                    logger.warn('get a different name of stock %s', stock_code)
                if section_category in stock_dict[stock_code]:
                    stock_dict[stock_code][section_category].append(section_name)
                else:
                    stock_dict[stock_code][section_category] = [section_name]

    for section_category, section_list in section_dict.items():
        for section in section_list:
            section_code, section_name = section
            cmd_code = 'C.BK0%s1' % section_code[5:8]
            stock_list = get_stock_list_of_section(cmd_code, section_name)
            _get_section_info(stock_list, section_category)

    other_section_categories = [('C._ME', u'中小版'), ('C.80', u'创业版')]
    for cmd_code, section_name in other_section_categories:
        stock_list = get_stock_list_of_section(cmd_code, section_name)
        _get_section_info(stock_list)

    stock_section_info_cache = stock_dict
    logger.info('-> get all stock section information finished')
    return stock_dict


def export_stock_section_info(use_cache=True):
    if not (use_cache and stock_section_info_cache):
        get_stock_section_info()
    else:
        logger.info('-> export with cached section information')
    text = json.dumps(stock_section_info_cache)
    human_text = json.dumps(
        stock_section_info_cache,
        indent=2,
        ensure_ascii=False
    ).encode('utf-8')

    with open('sections.json', 'w') as f:
        f.write(text)
    with open('sections_human.json', 'w') as f:
        f.write(human_text)
    logger.info('-> export stock section information finished')


if __name__ == '__main__':
    export_stock_section_info()
