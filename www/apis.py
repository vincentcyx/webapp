#!/usr/bin/python3

__author__ = 'vincent'

'''
JSON	API definition
'''

import json,logging,inspect,functools

class APIError(Exception):
	'''
	the base APIError which contains error(required),data(optionnal) and message(optional).
	'''
	def __init__(self,error,data='',message=''):
		super(APIError,self).__init__(messgae)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	
	'''
		Indicate the input value has error or invalid. the data specifies the error field of input form.

	'''

	def __init__(self,field,message=''):
		super(APIValueError,self).__init__('value:invalid',field,message)

class APIResourceNotFoundError(APIError):
	'''
	Indicate the resource was not found.the data specifies the resource name	'''
	def __init__(self,field,message=''):
		super(APIResouceNotFoundError,self).__init__('value:notfound',field,message)

class APIPermissionError(APIError):
	'''
	Indicate the api has no permission
	'''
	def __init_(self,messge=''):
		super(APIPermissionError,self).__init__('permission:forbidden','permisson',message)