import os
import json
import pymysql
import traceback
import warnings
import re as preg

# 导入 警告类 并把 警告 转换成 错误
warnings.filterwarnings('error')

class Db:

    __connect = 'local'
    __instance = {}
    __startTrans = False
    __configFile = 'config.json'
    __MysqlLink = {}
    __cursor = {}
    __setting = { # 设置
        'cursorType' : pymysql.cursors.DictCursor #默认的 游标类型 为 key value
    }

    """
    单列 实例化的 时候 new 自己
    """
    def __new__(cls ,*args,**kwargs):

        cls.__DataBaseConfigJson = None
        # 获取当前包的 根路径
        __pathlist = os.path.dirname(__file__).split('\\')
        __pathlist.pop()
        # 当前包的根目录
        packetRoot = '\\'.join(__pathlist)

        # 当前驱动的名称
        driverName = 'Mysql'

        # 配置文件的路径
        configFilePath = packetRoot + '\\DataBase\\' + cls.__configFile


        try:
            # 读取配置文件 并把json 转化成 字典 （索引数组）
            if not os.path.exists(configFilePath):
                raise ValueError('{} table is not exists'.format(configFilePath))

            fileIo = open(configFilePath, 'r', 1, 'UTF-8')
            cls.__DataBaseConfigJson = json.load(fileIo)[driverName]
            fileIo.close()

            if 'connect' in kwargs:
                cls.__connect = kwargs['connect']

            # 连接数据库 多次实例化 只连接 一次
            if cls.__connect not in cls.__MysqlLink :
                connect = cls.__DataBaseConfigJson[cls.__connect]
                cls.__MysqlLink[cls.__connect] = pymysql.Connect(**connect)
                cls.__cursor[cls.__connect] = cls.__MysqlLink[cls.__connect].cursor(cls.__setting['cursorType'])



        except IOError as e:
            print(traceback.print_exc())
            return False
        except Exception as e:
            print(traceback.print_exc())
            return False



        if cls.__connect not in cls.__instance.keys() :

            cls.__instance[cls.__connect] = object.__new__(cls)


        return cls.__instance[cls.__connect]

    """
    :param tabelName 表的名称
    """
    def __init__(self ,connect='local'):

        # 当前连接的key
        self.__connect = connect
        self.__sql = {
            'allow_type': ['SELECT', 'FIND', 'UPDATE', 'INSERT', 'DELETE','COUNT'],
            'field': '',
            'where': [],
            'order': '',
            'limit': [],
            'group': ''
        }
        self.sql = ''


    def table(self ,tableName=''):
        self.tableName = tableName
        if tableName != False and self.__checkTableExists(tableName) == 0 :
            raise ValueError('表不存在')
        
        return self.__instance[self.__connect]

    """
    检查表是否存在
    """
    def __checkTableExists(self ,tableName):
        return self.__cursor[self.__connect].execute('show tables like "%s"' % (tableName))

    """
    获取SQL语句类型
    """
    def __getSqlType(self):
        # 获取被哪个方法调用的
        sqlPrefix = traceback.extract_stack()[-3][-2]
        if(sqlPrefix == 'find' ):
            sqlPrefix = 'select'


        # 检查 被调用的方法 是否在 允许的 范围
        try:
            # list.index() 不再 列表里 会 抛出异常
            self.__sql['allow_type'].index(sqlPrefix.upper())
        except ValueError as e:
            raise ValueError(sqlPrefix + ' SQL 类型不被允许')

        self.__sql['sqlType'] = sqlPrefix

        if(sqlPrefix == 'select'):
            self.__sql['prifix'] = sqlPrefix.upper()

        if(sqlPrefix == 'insert'):
            self.__sql['prifix'] = sqlPrefix.upper() + ' INTO '

        if(sqlPrefix == 'delete'):
            self.__sql['prifix'] = sqlPrefix.upper() + ' FROM '

        if(sqlPrefix == 'update'):
            self.__sql['prifix'] = sqlPrefix.upper() + ' '

        if (sqlPrefix == 'count'):
            self.__sql['prifix'] = 'SELECT' + ' '


        return

    """
    组装sql
    """
    def __buildSql(self ,*args):

        self.__getSqlType()

        fieldStr = self.__filterField()

        if(self.__parseWhere(self.__sql['where']).__len__()):
            whereStr = ' WHERE ' + self.__parseWhere(self.__sql['where'])
        else:
            whereStr = ''

        limitStr = self.__limitToStr()


        try:

            if (['insert','update'].index(self.__sql['sqlType']) >= 0 ):
                return self.__sql['prifix'] + ' `'+self.tableName+'`' + self.__dataToSql(args[0]) + whereStr + limitStr

        except ValueError as e:
            return self.__sql['prifix'] + fieldStr + ' `' + self.tableName + '`' + whereStr + self.__sql['group'] + self.__sql[
                'order'] + limitStr

    """
    多条查询
    """
    def select(self):
        self.lastSql = self.__buildSql()
        result = self.__query(self.lastSql)
        self.__clearSelfAttr()
        if (result.__len__() == 0):
            return False
        else:
            return result

    def find(self):
        self.__sql['limit'] = [1]
        self.lastSql = self.__buildSql()
        result = self.__query(self.lastSql)

        self.__clearSelfAttr()

        if(result.__len__() == 0):
            return False;
        else:
            return result[0]

    def insert(self ,data = []):
        sql = self.__buildSql(data)
        self.lastSql = sql
        self.__clearSelfAttr()
        return self.__query(sql)

    def count(self):
        sql = self.__buildSql()
        self.lastSql = sql
        self.__clearSelfAttr()
        return self.__query(sql)

    def update(self ,data = []):

        sql = self.__buildSql(data)
        self.lastSql = sql
        self.__clearSelfAttr()
        return self.__query(sql)


    def startTrans(self):
        self.__startTrans = True
        self.__MysqlLink[self.__connect].begin()

    def rollback(self):
        self.__MysqlLink[self.__connect].rollback()
    def commit(self):
        self.__MysqlLink[self.__connect].commit()


    def __query(self ,sql = ''):
        try:
            # 没有开启事物的情况下 自动提交
            if(self.__startTrans == False):
                self.__MysqlLink[self.__connect].autocommit(1)

            flag = self.__cursor[self.__connect].execute(sql)
            if(self.__sql['sqlType'] == 'insert'):
                return self.__cursor[self.__connect].lastrowid
            if (self.__sql['sqlType'] == 'update'):
                return flag
            if(self.__sql['sqlType'] == 'select'):
                return self.__cursor[self.__connect].fetchall()

            if (self.__sql['sqlType'] == 'count'):
                res = self.__cursor[self.__connect].fetchall();
                return res[0]['count(*)']

        except Warning as e:
            self.__MysqlLink[self.__connect].rollback()
            raise Exception('sql warining :'+ str(e) + ' sql :'+ sql)

        except Exception as e:
            self.__MysqlLink[self.__connect].rollback()
            raise Exception('sql execute Error check your sql : '+ sql)

    def field(self ,fieldStr = ''):
        self.__sql['field'] = fieldStr if(fieldStr) else fieldStr;
        return self.__instance[self.__connect]

    def where(self ,whereList = []):
        if(type(whereList) != list):
            raise ValueError('where 值必须是list类型')
        self.__sql['where'] = (whereList if(whereList) else whereList)

        return self.__instance[self.__connect]

    def order(self , orderStr = ''):
        self.__sql['order'] = ' ORDER BY %s ' % (orderStr)
        return self.__instance[self.__connect]

    def group(self , groupStr = ''):
        self.__sql['group'] = ' GROUP BY %s ' % (groupStr)
        return self.__instance[self.__connect]

    def limit(self , limitList = []):
        self.__sql['limit'] = (limitList if (limitList) else [])
        return self.__instance[self.__connect]

    """
    数组组装成对应的 sql 字符串
    """
    def __dataToSql(self ,data = []):

        field = '('
        fieldList = []
        values = ' VALUES'
        if (type(data) != list):
            raise ValueError('insert 值必须是 list 列表 类型')

        if (self.__sql['sqlType'] == 'insert'):
            for k ,v in enumerate(data):
                if(type(v) != dict):
                    raise ValueError('insert 列表中的值，只可以是 dict 字典类型')
                values += '('
                for key ,value in v.items():
                    if(fieldList.count(key) == 0):
                        fieldList.append(key)
                    if isinstance(value ,str):
                        values += "\"%s\"," % (pymysql.escape_string(value))
                    elif value == None:
                        values += '%s ,' % 'NULL'
                    else:
                        values +=  '\'%s\' ,' % (value)

                values = values.strip(',')
                values += '),'

            for f in fieldList:
                f = "`%s`" % f
                field += f + ','

            # print(field.strip(',') + ') ' + values.strip(','))

            return field.strip(',') + ') ' + values.strip(',')


        if (self.__sql['sqlType'] == 'update'):
            for k ,v in enumerate(data):
                if (type(v) != dict):
                    raise ValueError('insert 列表中的值，只可以是 dict 字典类型')

                for key ,value in v.items():
                    _str = ' `%s` = "%s" ' % (key ,value)
                    fieldList.append(_str)
            return ' SET '+ ','.join(fieldList)


    """
    解析where参数 转换成 where 字符串
    """
    def __parseWhere(self ,whereExp = []):

        if(type(whereExp) != list and whereExp.__len__()):
            return ''

        whereList = []
        for k ,v in enumerate(whereExp):
            if (type(v) == list):
                _str = self.__parseWhere(v)
                whereList.append(_str)
            else:
                # ['exp' ,'instr(field,str)'] 这种格式
                if(whereExp[0].upper() == 'EXP' and len(whereExp[1]) > 0):
                    _str = whereExp[1]
                    if(whereList.count(whereExp[1]) == 0):
                        whereList.append(_str)
                # ['id' ,'=' ,1] 这种格式
                elif(len(whereExp[0]) > 0 and len(whereExp[1]) > 0 and len( str(whereExp[2]) ) > 0):

                    if whereExp[1] == 'in':
                        strList = []
                        for i in whereExp[2]:
                            strList.append(str(i))

                        strList = ','.join(strList)

                        _str = whereExp[0] +' '+ whereExp[1] + "(%s)" % (strList)

                    else:
                        _str = whereExp[0] +' '+ whereExp[1] + "'%s'" % (str(whereExp[2]))
                        if (whereList.count(_str) == 0):
                            whereList.append(_str)

                else:
                    continue

                return ''.join(whereList)


        return ' AND '.join(whereList)

    def __limitToStr(self):

        if(self.__sql['sqlType'] == 'insert'):
            return ''
        if( isinstance(self.__sql['limit'],list) != True ):
            raise ValueError('limit 值得类型必须是 list 列表')
        if(self.__sql['limit'].__len__() == 0):
            return ''
        if(self.__sql['limit'].__len__() > 2):
            raise ValueError('limit 列表对多两个值')

        if (self.__sql['limit'].__len__() == 1):
            return ' LIMIT %s ' % (self.__sql['limit'][0])

        if (self.__sql['limit'].__len__() == 2):
            return ' LIMIT %s,%s' % (self.__sql['limit'][0] ,self.__sql['limit'][1])


    def __filterField(self ):
        if self.__sql['sqlType'] == 'count':
            return  'count(*) FROM'

        field = ''
        for v in self.__sql['field'].split(','):
            if(v.__len__() > 0):
                field += ' `%s`,' % (v)
        if(field):
            return field.strip(',') + ' FROM'
        else:
            return ' * FROM'



    def query(self ,sql):
        try:

            if(preg.match('select',sql ,preg.I)):
                self.__cursor[self.__connect].execute(sql)
                return self.__cursor[self.__connect].fetchall()
            elif (preg.match('show', sql, preg.I)):
                self.__cursor[self.__connect].execute(sql)
                return self.__cursor[self.__connect].fetchall()
            else:
                result = self.__cursor[self.__connect].execute(sql)
                self.__MysqlLink[self.__connect][self.__connect].commit()
                return result
        except:
            print(traceback.print_exc())


    def __clearSelfAttr(self):
        self.__sql['field'] = ''
        self.__sql['where'] = []
        self.__sql['order'] = ''
        self.__sql['limit'] = []
        self.__sql['group'] = ''







    """
    获取刚刚执行的sql
    """
    def getLastSql(self):
        return self.lastSql

    """
    脚本执行完成 释放|删除 对象的时候
    """
    def __del__(self):

        self.__cursor[self.__connect].close()
        self.__MysqlLink[self.__connect].close()
        del self
        #print('--------------------del object close Mysql link--------------------')




"""
直接调用直接pass
"""
if __name__ == "main":
    pass





