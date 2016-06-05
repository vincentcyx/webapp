#!/usr/bin/python3

__author__ = 'vincent'

import asyncio,logging
import aiomysql

def log(sql,args=()):
	logging.info('SQL: %s' % sql)
#创建MySQL 连接池存放在全局变量__pool中 
@asyncio.coroutine
def create_pool(loop = None,**kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = yield from aiomysql.create_pool(
			host = kw.get('host','localhost'),
			port = kw.get('port',3306),
			user = kw['user'],
			password = kw['password'],
			db= kw['db'],
			charset = kw.get('charset','utf8'),
			autocommit = kw.get('autocommit',True),
			maxsize = kw.get('maxsize',10),
			minsize = kw.get('minsize',1),
			loop = loop
)

@asyncio.coroutine
def close_pool():
	logging.info('close database connection pool...')
	global __pool
	__pool.close()
	yield from __pool.wait_closed()
#执行select语句，需要传入sql语句和sql参数
@asyncio.coroutine
def select(sql,args,size=None):
	log(sql,args)
	global __pool
	with (yield from __pool) as conn:
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?','%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()

		yield from cur.close()
		logging.info('rows returnd: %s' % len(rs))
		return rs

#执行 insert update delete
@asyncio.coroutine
def execute(sql,args):
	log(sql)
	with (yield from __pool) as conn:
#		yield from conn.begin()
		try:
			cur = yield from conn.cursor(aiomysql.DictCursor) 
			affected = yield from cur.execute(sql.replace('?','%s'),args)
			yield from cur.close()
			#yield from conn.commit()
		except BaseException as e:
			#yield from conn.rollback()
			raise
		return affected

def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ','.join(L)

##########定义ORM对象
#定义所有orm映射的基类Model
class ModelMetaclass(type):
	#元类使用__new__来创建类或修改类
	#__new__ 参数1 当前准备创建的类的对象
 	#param2 类的名字
	#param3 类继承的父类集合
	#类的方法集合
	def __new__(cls,name,bases,attrs):
		#排除Model类
		if name == 'Model':
			return type.__new__(cls,name,bases,attrs)
		#获取tablename
		tableName = attrs.get('__table__',None) or name
		logging.info('found Model: %s (table: %s)' % (name,tableName))
		#获取所有Field和主键名:
		mappings = dict()
		fields = []
		primarykey = None
		for k,v in attrs.items():
			if isinstance(v,Field):
				logging.info(' 	found mapping: %s ==> %s' %(k,v))
				mappings[k] = v
				if v.primary_key:
					if primarykey:
						raise RuntimeError('Duplicate primary key for field:%s' % k)
					primarykey = k
				else:
					fields.append(k)
		if not primarykey:
			raise RuntimeError('Primary key not found')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f:'`%s`' % f,fields))
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		attrs['__primary_key__']  = primarykey
		attrs['__fields__'] = fields
		attrs['__select__'] = 'select `%s`,%s from `%s` ' % (primarykey,','.join(escaped_fields),tableName)
		attrs['__insert__'] = 'insert into `%s` (%s,`%s`) values(%s)' % (tableName, ','.join(escaped_fields),primarykey,create_args_string(len(escaped_fields)+1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=? '% (tableName,','.join(map(lambda f: '`%s` = ?' % (mappings.get(f).name or f),fields)),primarykey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName,primarykey)
		return type.__new__(cls,name,bases,attrs)


class Model(dict,metaclass=ModelMetaclass):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)


	def getValue(self,key):
		return getattr(self,key,None)

	def getValueOrDefault(self,key):
		value = getattr(self,key,None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s : %s' % (key,str(value)))
				setattr(self,key,value)
		return value


	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self,key,value):
		self[key] = value
	#@classmethod 
	@classmethod
	@asyncio.coroutine
	def findAll(cls,where = None, args=None,**kw):
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy',None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit,tuple) and len(limit) == 2:
				sql.append('?,?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value : %s' % str(limit))
		rs = yield from select(' '.join(sql),args)
		return [cls(**r) for r in rs]

	@classmethod
	@asyncio.coroutine
	def findNumber(cls,selectField,where = None,args = None):
		sql =['select %s _num_ from `%s` ' % (selectField,cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql),args,1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']
	
	@classmethod
	@asyncio.coroutine
	def find(cls,pk):
		rs = yield from select('%s where `%s`=?' %(cls.__select__,cls__primary_key__),[pk],1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])


	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = yield from execute(self.__insert__,args)
		if rows != 1:
			logging.warn('failed to insert record : affected rows: %s' % rows)

	@asyncio.coroutine
	def update(self):
		args = list(map(self.getValue,self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = yield from execute(self.__update__,args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows : %s' % rows)

	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key_)]
		rows = yield from execute(self.__delete__,args)
		if rows != 1:
			logging.warn('failed to remove by rpimary key: affected rows %s ' % rows)
class Field(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s , %s , %s' % (self.__class__.__name__,self.column_type,self.name)

class StringField(Field):
	def __init__(self,name = None,primary_key=False,default = None,ddl = 'varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

class IntegerField(Field):
	def __init__(self,name = None,primary_key = False, default = 0, ddl = 'bigint'):
		super().__init__(name,ddl,primary_key,default)
class BooleanField(Field):
	def __init__(self,name = None,default = False):
		super().__init__(name,'boolean',False,default)
	
class FloatField(Field):
	def __init__(self,name = None,primary_key = False,default = 0.0):
		super().__init__(name,'real',primary_key,default)
class TextField(Field):
	def __init__(self,name = None,default = None):
		super().__init__(name,'text',False,default)


