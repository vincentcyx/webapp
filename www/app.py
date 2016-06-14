#!/usr/bin/python3
#  Web App骨架 在9000端口监听请求

import logging
import asyncio
import os
import json
import time
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
import orm
from coroweb import add_routes, add_static
logging.basicConfig(level=logging.DEBUG)


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_strig', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 templeate path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        '''
            this is a middleware for web.Application before handle the url do something
            this method is a coroutine it logging the request information
            this corutine should accept two parameters an app instance and a handler
            and return a new handler . the new handler has the same signature as a request
            handler. The last middleware factory has request a response
        '''
        logging.info('Request: %s %s' % (request.method, request.path))
        return (yield from handler(request))
    return logger


@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        '''
            the middleware for web.Application before handle the url do something
            这是一个用来做拦截器的装饰器，在web.Application中使用
            在处理URL前 如果是post请求，先获取post的数据
        '''
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (yield from handler(request))
    return parse_data


@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        '''
            this method should ruturn a request a dict-like or a response instance
            like ResponseStream
            this coroutine is make the response instance by requst
        '''
        logging.info('Response handler ...')
        result = yield from handler(request)
        if isinstance(result, web.StreamResponse):
            return result
        if isinstance(result, bytes):
            resp = web.Response(body=result)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(result, str):
            if result.startswith('redirect:'):
                #  如果请求的结果以redirect开头的字符串 重定向到URL
                return web.HTTPFound(result[9:])
        if isinstance(result, dict):
            template = result.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(result, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset = utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**result).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(result, int) and result >= 100 and result <600:
            return web.Response(result)
        if isinstance(result, tuple) and len(result) == 2:
            t, m = result
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        #  default
        resp = web.Response(body=str(result).encode('utf-8'))
        resp.content_type = 'text/plain;charset = utf-8'
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


@asyncio.coroutine
def init(loop):
    yield from orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='www-data', password='www-data', db='awesome')
    #  middlewares 是一种拦截器，它们是一个队列，在handle函数处理URL前，做一些通用的
    #  处理，比如日志输出 一个拦截器是一个装饰器
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = yield from loop.create_server(app.make_handler(), '0.0.0.0', 9000)
    logging.info('server startd at any ip on 9000')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
