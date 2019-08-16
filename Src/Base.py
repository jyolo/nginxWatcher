import traceback,os,sys
from DataBase.Mongo import MongoDb
from DataBase.Redis import Redis
from Src.ip2Region import Ip2Region


"""
python 递归超过一定深度就会　栈溢出　
尾递归的优化
勿删除　否则长时间　运行会　栈溢出
"""

class TailRecurseException(BaseException):
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs
def tail_call_optimized(g):
    """
    This function decorates a function with tail call
    optimization. It does this by throwing an exception
    if it is it's own grandparent, and catching such
    exceptions to fake the tail call optimization.

    This function fails if the decorated
    function recurses in a non-tail context.
    """
    def func(*args, **kwargs):
        f = sys._getframe()
        if f.f_back and f.f_back.f_back and f.f_back.f_back.f_code == f.f_code:
            raise TailRecurseException(args, kwargs)
        else:
            while 1:
                try:
                    return g(*args, **kwargs)
                except TailRecurseException as e:
                    args = e.args
                    kwargs = e.kwargs
    func.__doc__ = g.__doc__
    return func

class Base:

    def __init__(self ,logPath = None, redisKey = None , proccessNum = 2 , withStatic = False):

        if(self.__class__.__name__ == 'Reader'):
            if (os.path.exists(logPath) == False):
                raise FileNotFoundError('logfile is not exsits')
            self.logPath = logPath

        # elif(self.__class__.__name__ == 'Writer'):
        #     self.logPath = logPath
        #     self.listKey = self.logPath.replace('.', '_')

        self.listKey = redisKey
        self.proccessNum = proccessNum
        self.withStatic = withStatic


        # redis
        self.redis = None
        self.redisDbNum = 3
        self.emptyLineMaxTime = 10

        # mongodb
        self.mongodb = None
        self.dbName = 'xfb'
        self.dbCollection = None
        self.insertData = []
        self.insertDataMaxLen = 50




    def getRedis(self):

        if (self.redis == None):
            try:
                print('init redis')
                self.redis = Redis(self.redisDbNum).db
            except Exception as e:
                traceback.print_exc()
                exit(0)


        return self.redis

    def getMongoDB(self ,log_date_format):
        collection = self.listKey + '_%s' % log_date_format
        change_days = (self.dbCollection == collection)

        if(self.mongodb == None or change_days == False):
            print('init mongodb')
            self.dbCollection = collection
            self.mongodb = MongoDb(self.dbName, self.dbCollection).db


        return self.mongodb

    def ipLocation(self,ip):

        try:

            ipDbPath = os.path.dirname(os.path.abspath(__file__)) + '/ip2region.db'
            self.ipDb = Ip2Region(ipDbPath)
            ip_result = self.ipDb.binarySearch(ip)
            location = ip_result['region'].decode('utf-8').split('|')

            return location

        except Exception as e:
            print('ip库 定位失败')
            # traceback.print_exc()
            return  False

    # log pid
    def logPid(self ,readType = 'w+'):
        f = open('readLogWorker.pid', readType)
        if readType == 'w+':
            f.write('%s' % os.getpid())
        elif readType == 'a+':
            f.write(' %s' % os.getpid())
        f.close()

    def get_FileSize(self ,filePath):
        fsize = os.path.getsize(filePath)
        fsize = fsize / float(1024 * 1024)
        return round(fsize, 2)
