#!/usr/bin/python3
'''
#!/usr/bin/python3
    url handlers

'''
from coroweb import get
import asyncio
from models import User
#  from coroweb import post
#  import re,time,json,logging,hashlib,base64,asyncio
#  from coroweb import post
#  from models import User,Comment,Blog,next_id
__author__ = 'Vincent'


@get('/')
@asyncio.coroutine
def index(request):
    '''
       A request handler can be any callable that accepts a Request instance as its only
       argument and returns a StreamResponse derived(派生) instance
    '''
    users = yield from User.findAll()
    logging.info("get request proces")
    return {
        '__template__': 'test.html',
        'users': users
    }
