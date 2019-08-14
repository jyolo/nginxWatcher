import time,re,traceback,os,sys
from multiprocessing import Pool
from DataBase.Mongo import MongoDb
from DataBase.Redis import Redis
from redis.exceptions import RedisError
from pymongo.errors import PyMongoError
from ip2Region import Ip2Region

"""
python nginxWatcher -f _logpath 
"""


class Base:

    def __init__(self ,logPath):

        if(self.__class__.__name__ == 'Reader'):
            if (os.path.exists(logPath) == False):
                raise FileNotFoundError('logfile is not exsits')
            self.logPath = logPath
            self.listKey = logPath.split('/')[-1].replace('.', '_')
        else:
            self.logPath = logPath
            self.listKey = self.logPath.replace('.', '_')



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

            ipDbPath = './ip2region.db'
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


class Reader(Base):


    def startTailf(self):

        with open(self.logPath, newline="\n") as f:
            emptyTimes = 0
            redisRtryTimes = 0
            f.seek(0, 2)
            while 1:
                try:
                    time.sleep(0.1)
                    for line in f:
                        emptyTimes = 0
                        flag = (self.getRedis()).lpush(self.listKey, line)
                        #print(flag)

                    """
                    文件没有内容的时候　不进入　for in 中　则　raise StopIteration　错误　
                    循环尝试超过　指定次数后　则关闭文件从新打开文件
                    """
                    raise StopIteration('暂无数据')

                except StopIteration as e:
                    emptyTimes = emptyTimes + 1
                    if (emptyTimes == 1):
                        continue

                    if(emptyTimes >= self.emptyLineMaxTime):
                        time.sleep(1)
                        f.close()
                        self.startTailf()
                    else:

                        time.sleep(0.1)
                        print('empty line %s time' % emptyTimes)


                except RedisError as e:
                    redisRtryTimes = redisRtryTimes + 1
                    self.redis = None
                    time.sleep(1)
                    # redis 报错之后　程序挂机一直尝试
                    print('redis error retrying %s times' % redisRtryTimes)
                    if(redisRtryTimes >= 100):
                        print('retry over 100 times proccess exit')
                        exit(0)

                except Exception as e:
                    # 其它未知错误　直接退出
                    traceback.print_exc()
                    exit(0)


class Writer(Base):

    def start(self ,withStatic = False):
        redisRtryTimes = 0
        mongodbRtryTimes = 0

        while 1:
            try:

                time.sleep(0.1)
                line = (self.getRedis()).lpop(self.listKey)
                if(line == None):
                    time.sleep(1)
                    print('pid : %s waiting for line data' % os.getpid())
                    continue

                self.lineLogToMongo(line ,withStatic)
                # 重试次数归零
                redisRtryTimes = 0
                mongodbRtryTimes = 0

            except RedisError as e:
                redisRtryTimes = redisRtryTimes + 1
                self.redis = None
                time.sleep(1)
                # redis 报错之后　会一直重试知道超出重试值
                print('redis error retrying %s times' % redisRtryTimes)
                if (redisRtryTimes >= 100):
                    print('retry over 100 times proccess exit')
                    exit(0)
            except PyMongoError as e:
                mongodbRtryTimes = mongodbRtryTimes + 1
                self.mongodb = None
                time.sleep(1)
                # mongodb 报错之后　程序挂机一直尝试
                print('mongodb error retrying %s times' % mongodbRtryTimes)
                if (mongodbRtryTimes >= 100):
                    print('retry over 100 times proccess exit')
                    exit(0)


    def lineLogToMongo(self ,line,withStatic ):
        #####
        # nginx log format
        #'[$time_local] $host $remote_addr - "$request" '
        #'$status $body_bytes_sent "$http_referer" '
        #'"$http_user_agent" "$http_x_forwarded_for"';
        ####

        line = line.strip()
        _arr = line.split(' ')


        # filter static file 如果　-static 则　withStatic = True
        if(withStatic == False):
            if (re.search(r'\.[js|css|png|jpg|ico|woff]', _arr[6].strip(''))):
                # print('it`s static request')
                return

        _map = {}
        request_time = _arr[0].strip('').strip('[')
        request_time.replace('[', '')

        time_int = time.mktime(time.strptime(request_time, "%d/%b/%Y:%H:%M:%S"))
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time_int)))

        _map['time_str'] = time_str
        _map['time_int'] = int(time_int)

        _map['status'] = _arr[8].strip('')
        _map['content_size'] = _arr[9].strip('')
        _map['referer'] = _arr[10].strip('').strip('"')
        _map['web_site'] = _arr[2].strip('')
        _map['ip'] = _arr[3].strip('')

        # ip 匹配是否市 合法ip
        trueIp = re.search(r'(([01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])\.){3}([01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])', _map['ip'])
        if(not trueIp):
            print('ip match error')
            return


        ip2location = self.ipLocation(_map['ip'])
        if (ip2location == False):
            print('ip2location matcg fail')
            _map['country'] = ''
            _map['region'] = ''
            _map['province'] = ''
            _map['city'] = ''
            _map['isp'] = ''
        else:
            _map['country'] = ip2location[0]
            _map['region'] = ip2location[1]
            _map['province'] = ip2location[2]
            _map['city'] = ip2location[3]
            _map['isp'] = ip2location[4]


        _map['method'] = _arr[5].strip('').strip('"')
        _map['url'] = _arr[6].strip('')



        # ua and x_forward_for

        last_part = line.split(' "')

        _map['user_agent'] = last_part[-2].strip('"')
        # _map['http_x_forwarded_for'] = last_part[-1].strip('"')
        #
        #
        # if(re.search(r'-',_map['http_x_forwarded_for'])):
        #     _map['http_x_forwarded_for'] = _map['http_x_forwarded_for'].strip('"')
        # else:
        #     iplist = _map['http_x_forwarded_for'].split(',')
        #     x_iplist = ''
        #     for i in iplist:
        #         x_ip = i.strip()
        #         ip_result = self.ipDb.binarySearch(x_ip)
        #         location = ip_result['region'].decode('utf-8')
        #         x_iplist += '%s,%s' % (x_ip ,location) + '->'
        #     _map['http_x_forwarded_for'] = x_iplist.strip('->')


        # 数据追加到 列表中
        self.insertData.append(_map)

        # print(len(self.insertData))

        # 当满足设定的数量 则入库
        if(len(self.insertData) >= self.insertDataMaxLen):

            Collection = time_str.split(' ')[0]
            mid = (self.getMongoDB(Collection)).insert_many(self.insertData)
            if(mid):
                print('pid: %s insert success' % os.getpid())

            # 写入成功后清空数据列表
            self.insertData = []



def read(logPath):
    Reader(logPath).startTailf()

def write(logFileName ,withStatic):

    Writer(logFileName).start(withStatic)


if __name__ == "__main__":

    try:
        path_commond = sys.argv[1]

        if ('-m' in sys.argv):
            runModel = sys.argv[ sys.argv.index('-m') + 1 ].strip()
            if(runModel not in ['read' ,'write','both']):
                raise IndexError('未匹配到命令')
        else:
            runModel = 'both'

        if('-p' in sys.argv):
            writerProccessNum = sys.argv[ sys.argv.index('-p') + 1 ].strip()
            writerProccessNum = int(writerProccessNum)
        else:
            writerProccessNum = 2

        if ('-with-static' in sys.argv):
            withStatic = True
        else:
            withStatic = False

        if (path_commond == '-f'):
            logPath = sys.argv[2]


        """
        按照模式运行
        """
        if(runModel == 'both'):

            pollNum = writerProccessNum
            poll = Pool(pollNum)

            for i in range(pollNum):
                poll.apply_async(write,args=(logPath,withStatic,))

            read(logPath)

            poll.close()
            poll.join()


        elif(runModel == 'read'):
            read(logPath)

        elif(runModel == 'write'):

            pollNum = writerProccessNum
            poll = Pool(pollNum)

            for i in range(pollNum):
                poll.apply_async(write,args=(logPath,withStatic,))

            poll.close()
            poll.join()




    except Exception as e:
        traceback.print_exc()
        print('-----------------------------------doc----------------------------------- ')
        print('| args  : ')
        print('|    support args : ')
        print('|    -f  your access.log path  ')
        print('|    -m  run model -m [read | write | both]  ')
        print('|    -p  writer Proccess Number  ')
        print('|    -with-static  writer Proccess will not filter static file request  ')
        print('| only read log; for example: python3 -u watcher.py -f  /wwwlogs/access.log -m read   ')
        print('| only write log; for example: python3 -u watcher.py -f  /wwwlogs/access.log -m write -p 4   ')
        print('| read and write log; for example: python3 -u watcher.py -f  /wwwlogs/access.log [ -m both -p 2]   ')
        print('-----------------------------------doc----------------------------------- ')


