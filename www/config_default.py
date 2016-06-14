#!/usr/bin/python3

'''
    Default Configurations.
'''

__author__ = 'Vincent'

configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'usr': 'www-data',
        'password': 'www-data',
        'db': 'awesome'
    },
    'session': {
        'secret': 'Awesome'
    }

}
