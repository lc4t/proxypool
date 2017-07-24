#! /usr/local/bin/python2
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

import time
import requests
from bs4 import BeautifulSoup
# from queue import Queue
from Queue import Queue
from gevent.pool import Pool
import gevent.monkey
from gevent.local import local
import random
import json
from pyv8 import PyV8
import logging
from colorlog import ColoredFormatter

# logger
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)-8s %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
},
secondary_log_colors={},
style='%'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
## END


class proxy:
    def __init__(self):
        self.ip = ''
        self.port = 0
        self.scheme = 'http'
        self.safe = ''
        self.place = ''
        self.net = None
        self.verify = 0
        self.delay = 0


    def __str__(self):
        s = '<{scheme}://{ip}:{port}> {safe} {place} {last_verify}'
        t = int((time.time()-self.verify)*1000)/1000
        last_verify = 'verify before %ds' % t if self.verify != 0 else 'not verify'
        return s.format(scheme=self.scheme, ip=self.ip, port=self.port, safe=self.safe, place=self.place, last_verify=last_verify)

    def dic(self):
        return {
            'ip': self.ip,
            'port': self.port,
            'scheme': self.scheme,
            'safe': self.safe,
            'place': self.place,
            'net': self.net,
            'delay': self.delay,
        }






class ProxyPool:


    def __init__(self):
        self.THREAD_ID = 0
        self.proxy_list = []
        self.wait_for_verify = Queue()
        self.thread_pool = Pool()
        self.output = []
        gevent.monkey.patch_socket()
        gevent.monkey.patch_ssl()
        # self.thread_pool.start()

    def http_headers(self):
        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Chrome/59.0.%d.%d Safari/537.36' % (random.randint(1000, 9999), random.randint(100, 999)),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.8'
        }
        return headers

    def add_thread(self, func, *args):
        # print('test')
        if self.thread_pool.full():
            raise Exception("At maximum pool size")
        else:
            self.thread_pool.spawn(func, *args)
            # self.thread_pool.join()

    def add_proxy(self, proxy):
        self.proxy_list.append(proxy)

        self.output.append(proxy.dic())
        # print(self.output)
        self.output = sorted(self.output, key=lambda k: k['delay'])
        open('proxy.json', 'w').write(json.dumps(self.output, ensure_ascii=True, indent=4))


    def kill_thread(self):
        self.thread_pool.kill()

    def start(self):
        self.add_thread(self.kuaidaili_com)
        self.add_thread(self.goubanjia_com)
        self.add_thread(self._66ip_cn)
        self.thread_pool.join()

    def get(self):
        pass

    def get_all(self):
        return self.proxy_list


    def kuaidaili_com(self, *args):
        self.add_thread(self.kuaidaili_type_com, 'inha')
        self.add_thread(self.kuaidaili_type_com, 'intr')
        self.add_thread(self.kuaidaili_type_com, 'outha')
        self.add_thread(self.kuaidaili_type_com, 'outtr')

    def kuaidaili_type_com(self, t, *args):
        logger.info('kuaidaili.com %s start' % t)
        i = 1
        self.THREAD_ID += 1
        rq = requests.Session()
        headers = self.http_headers()
        rq.get('http://www.kuaidaili.com/', headers=headers)
        while(1):
            gevent.sleep(3)
            url = 'http://www.kuaidaili.com/free/%s/%d/' % (t, i)
            r = rq.get(url, headers=headers)
            if 'qo=eval;qo(po);' in r.text:
                c = PyV8.JSContext()
                c.enter()
                f = c.eval(r.text)
                print(f)
                # exit()
                print(r.text)
                logger.debug('bypass...')
                continue
            if r.status_code == 404:
                break
            if r.status_code == 503:
                logger.error('%s return <%d>' % (url, r.status_code))
                continue
            try:
                html = BeautifulSoup(r.text, 'lxml')
                tbody = html.tbody
                if tbody is None:
                    print(html)
                    continue
                for tr in tbody.find_all('tr'):
                    # print(tr)

                    p = proxy()
                    p.ip = tr.find_all('td', {'data-title':"IP"})[0].text
                    p.port = int(tr.find_all('td', {'data-title':"PORT"})[0].text)
                    p.safe = tr.find_all('td', {'data-title':"匿名度"})[0].text
                    p.type = tr.find_all('td', {'data-title':"类型"})[0].text
                    p.place = tr.find_all('td', {'data-title':"位置"})[0].text

                        # print(tr.find_all('td', {'data-title':"响应速度"})[0].text)
                    # print(tr.find_all('td', {'data-title':"最后验证时间"})[0].text)
                    logger.debug('<get>%s' % p)
                    self.wait_for_verify.put(p)
                    self.THREAD_ID += 1
                    self.add_thread(self.verify_proxy_thread, self.THREAD_ID)
                logger.debug('%s ok' % url)
                gevent.sleep(1)
            except AttributeError as e:
                print(e)
                # print(r.text)

                logger.error('%s Error, sleep 10s' % url)
                gevent.sleep(10)
                continue

            # exit()
            i += 1


    def goubanjia_com(self, *args):
        logger.info('giubanjia.com start')
        i = 1
        self.THREAD_ID += 1
        while(1):
            url = 'http://www.goubanjia.com/free/index%d.shtml' % (i)
            r = requests.get(url, headers=self.http_headers())
            if r.status_code == 404:
                break
            try:
                html = BeautifulSoup(r.text, 'lxml')
                tbody = html.tbody
                for tr in tbody.find_all('tr'):
                    p = proxy()

                    [x.extract() for x in tr.find_all('p')]


                    try:
                        _ = tr.find_all('td', {'class':"ip"})[0].text
                        _ = _.split(':')
                        p.ip = _[0]
                        p.port = int(_[1])
                        # p.port = int(tr.find_all('td', {'data-title':"PORT"})[0].text)

                        p.safe = tr.find_all('td')[1].text.replace(' ', '').replace('\n', '').replace('\t', '')
                        p.type = tr.find_all('td')[2].text.replace(' ', '').replace('\n', '').replace('\t', '')
                        p.place = tr.find_all('td')[3].text.replace(' ', '').replace('\n', '').replace('\t', '').replace('\r', '').replace('\xa0', '')
                        p.net = tr.find_all('td')[4].text.replace(' ', '').replace('\n', '').replace('\t', '')
                    except IndexError as e:
                        print(tr)
                        logger.error('%s is index error' % p)
                        # exit(0)

                    logger.debug('<get>%s' % p)
                    self.wait_for_verify.put(p)
                    self.THREAD_ID += 1
                    self.add_thread(self.verify_proxy_thread, self.THREAD_ID)
                logger.debug('%s ok' % url)
                gevent.sleep(1)
            except AttributeError as e:
                print(e)
                # print(r.text)
                gevent.sleep(10)
                logger.error('%s Error, sleep 10s' % url)
                continue

            # exit()
            i += 1

    def _66ip_cn(self, *args):
        logger.info('giubanjia.com start')
        i = 1
        self.THREAD_ID += 1
        while(1):
            url = 'http://www.66ip.cn/%d.html' % (i)
            r = requests.get(url, headers=self.http_headers())
            if r.status_code == 404:
                break
            try:
                html = BeautifulSoup(r.content.decode('gb2312'), 'lxml')
                tbody = html.find_all('table')[2]

                for tr in tbody.find_all('tr'):
                    p = proxy()
                    _ = tr.find_all('td')[0].text
                    if _ == 'ip':
                        continue
                    else:
                        p.ip = _

                    p.port = int(tr.find_all('td')[1].text)

                    p.place = tr.find_all('td')[2].text
                    p.safe = tr.find_all('td')[3].text



                    logger.debug('<get>%s' % p)
                    self.wait_for_verify.put(p)
                    self.THREAD_ID += 1
                    self.add_thread(self.verify_proxy_thread, self.THREAD_ID)
                logger.debug('%s ok' % url)
                gevent.sleep(1)
            except AttributeError as e:
                print(e)
                # print(r.text)

                logger.error('%s Error, sleep 10s' % url)
                gevent.sleep(10)
                continue

            # exit()
            i += 1



    def get_delay(self, p):
        r = 0
        try:
            # r = requests.get('http://www.baidu.com', proxies={p.scheme: '%s:%d' % (p.ip, p.port)}).elapsed.microseconds/100000
             r = requests.get('http://www.baidu.com', proxies={p.scheme: '%s:%d' % (p.ip, p.port)}).elapsed
             r = r.seconds + (r.microseconds + 0.0)/1000000

        except requests.exceptions.ProxyError:
            return 0
        # except ConnectionError:
        #     return 0
        # except ConnectionResetError:
        #     return r
        except:
            # logger.error(str(p) + ' cannot get delay)
            return 0
        return r

    def verify_proxy_thread(self, thread_id):
        # logger.debug('<thread %d> start' % thread_id)
        if self.wait_for_verify.empty():
            # logger.debug('<thread %d> exit' % thread_id)
            self.THREAD_ID -= 1
            return None
            # if t <= 0:
            #     logger.info('<thread %d> exit' %  thread_id)
            #     return
            # else:
            #     logger.debug('<thread %d> wait for 1s' %  thread_id)
            #     gevent.sleep(1)
            #     return self.verify_proxy_thread(thread_id, t-1)

        p = self.wait_for_verify.get()
        delay = self.get_delay(p)


        if delay > 0:
            p.delay = delay
            p.verify = time.time()
            self.add_proxy(p)
        # for td in tr.find_all('td'):
        #     print(td.text)
            logger.info('<thread %d> get a proxy %s' % (thread_id, p))
        else:
            pass
            # logger.debug('<thread %d> throw away a proxy %s' % (thread_id, p))
        return self.verify_proxy_thread(thread_id)


if __name__ == '__main__':
    _ = ProxyPool()
    _.start()
