﻿# encoding='utf-8'

# pylint: disable=c0111,c0325

import json
import logging
import os
import re
import sys
from urllib import urlencode

import requests

from bs4 import BeautifulSoup
import dateutil.parser


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


# http://data.eastmoney.com/notices/getdata.ashx?StockCode=000004&CodeType=1&PageIndex=2&PageSize=700&SecNodeType=0&FirstNodeType=0&rt=49450435
idx_addr = 'http://data.eastmoney.com/notices/getdata.ashx?' \
'StockCode=%(stock_code)s&CodeType=1&jsObj=idx&PageIndex=%(page_idx)s&PageSize=%(page_size)d&SecNodeType=0&FirstNodeType=0&rt=49450435'
page_addr = 'http://data.eastmoney.com/notices/detail/%(stock_code)s/%(info_code)s,JUU1JTlCJUJEJUU1JTg2JTlDJUU3JUE3JTkxJUU2JThBJTgw.html'

HEADERS = {
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding':'gzip, deflate, sdch',
    'Accept-Language':'en,zh-CN;q=0.8,zh;q=0.6,zh-TW;q=0.4,ja;q=0.2',
    'Cache-Control':'no-cache',
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
}

SPLIT = '\r\n\r\n=====================\r\n\r\n'


def validate_title(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/\:*?"<>|'
    new_title = re.sub(rstr, "", title.replace(':', '_', 1))
    return new_title


def read_index(stock_code, page_idx):
    url = idx_addr % {
        'stock_code': stock_code,
        'page_idx': page_idx,
        'page_size': 100,
    }
    print '[get index] %s' % url
    resp = requests.get(url, headers=HEADERS)
    assert resp.status_code == 200, 'get index error'

    return json.loads(resp.content.decode('gbk').lstrip('var idx = ').rstrip(';'))


def read_page(stock_code, info_code):
    url = page_addr % {
        'stock_code': stock_code,
        'info_code': info_code,
    }
    print '[get page] %s' % url
    resp = requests.get(url, headers=HEADERS)
    assert resp.status_code == 200, 'get page error'

    soup = BeautifulSoup(resp.content, 'html.parser', from_encoding='gbk')
    detail_body = soup.find_all('div', {'class': 'detail-body'})
    assert len(detail_body) == 1
    detail_body = detail_body[0]

    return detail_body.text.replace(u'[点击查看PDF原文]', ''), url


def load_stock(stock_code):
    count = 1
    while True:
        idx_content = read_index(stock_code, count)
        if not idx_content['data']:
            break
        for info in idx_content['data']:
            filename = '%s_%s.txt' % (
                dateutil.parser.parse(info['NOTICEDATE']).strftime('%Y-%m-%d'),
                validate_title(info['NOTICETITLE']),
            )
            folder = '%s_%s' % (stock_code, info['CDSY_SECUCODES'][0]['SECURITYSHORTNAME'])
            folder = os.path.join(stock_code, folder)
            if not os.path.isdir(folder):
                os.mkdir(folder)
            filename = os.path.join(folder, filename)

            if os.path.exists(filename):
                continue

            try:
                page_text, url = read_page(stock_code, info['INFOCODE'])
            except:
                continue
            page_text = SPLIT.join([
                info['NOTICETITLE'],
                url,
                page_text,
            ])

            print '%s.txt' % info['NOTICETITLE'].encode('utf-8')

            with open(filename, 'w') as f:
                f.write(page_text.encode('utf-8'))
        count += 1


if __name__ == '__main__':
#     load_stock('000004')
    if sys.argv[1]:
        print '--------\nbegin <%s>\n--------' % sys.argv[1]
        load_stock(sys.argv[1])
    print '--------\nfinish\n--------'
