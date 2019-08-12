import os,time,re,traceback,os
from multiprocessing import Pool
from DataBase.Mongo import MongoDb
from DataBase.Redis import Redis
from pymongo.errors import *
from ip2Region import Ip2Region

class nginxLogWatcher:

    def __init__(self ,logPath ,toMongo = False):
        print('--start time : %s' % time.time())
        if(os.path.exists(logPath) == False):
            raise FileNotFoundError('logfile is not exsits')



        self.logPid()
        self.file_path = logPath
        self.file = open(logPath ,newline='\n')
        self.ipDb = None
        self.redisDbNum = 3
        self.list_key = 'nginx_log'
        self.redis = False


        self.insertData = []
        self.insertData_max_len = 50

        if toMongo == False:
            self.startTailF2()
            # self.startTailF()
            self.file.close()

    #  45474
    #  1829130

    def startTailF2(self):

        # 514368
        # 1527372
        start_size = self.get_FileSize(self.file_path)

        with open(self.file_path ,newline="\n") as f:

            f.seek(0,2)
            while 1:
                time.sleep(0.1)
                while_size = self.get_FileSize(self.file_path)
                print('---%s --%s while continue \n' % (f.tell() ,while_size) )

                # 当日志被切割之后　文件　大小肯定会小于　访问之间的体积
                if(while_size < start_size):
                    print('----%s-----%s' % (while_size ,start_size))
                    time.sleep(1)
                    f.close() # 释放文件资源
                    if (getattr(self, 'ipDb') != None):
                        self.ipDb.close() # 释放ipdb 的　socket

                    self.startTailF2()


                for line in f:

                    print(line )

                    # 当前获取不到记录的时候 把文件指针 指向文件头部
                    if (line == ''):
                        print('# 读到空行%s数' % empty_line_time)
                        time.sleep(0.1)
                        if empty_line_time >= 10:
                            print('reopen file waiting for line')
                            f.close()
                            if (getattr(self, 'ipDb') != None):
                                self.ipDb.close()
                            self.startTailF()
                        else:
                            empty_line_time = empty_line_time + 1
                            continue

                    empty_line_time = 0
                    # 保持存储集合按天分割
                    totday = time.strftime("%Y_%m_%d", time.localtime(time.time()))
                    self.dbCollection = 'xfb_online_%s_log' % totday

                    # print('------------%s---------------->\n' % time.time())
                    # print(line)
                    # print('------------%s---------------->\n' % time.time())

                    self.getRedis()
                    flag = self.redis.lpush(self.list_key, line)
                    print(flag)



    def get_FileSize(self ,filePath):
        fsize = os.path.getsize(filePath)
        fsize = fsize / float(1024 * 1024)
        return round(fsize, 2)

    def startTailF(self ):

        with open(self.file_path,'r+' ,newline='\n') as f:

            f.seek(0, 2)
            # 当文件被切割或者文件被修改过后 由于 文件指针已经被改变 会始终读取不到数据
            # empty_line_time 为计数器，当始终无法获取数据 超过一定次数 则关闭文件句柄 从新
            # 打开文件 并把指针指向文件末尾从新读取文件
            # 计数器 可根据网站流量
            empty_line_time = 0
            read_line_total = 0
            while 1:
                time.sleep(0.01)
                line = f.readline()

                # 当前获取不到记录的时候 把文件指针 指向文件头部
                if(line == ''):
                    print('# 读到空行%s数' % empty_line_time)
                    time.sleep(0.1)
                    if empty_line_time >= 10:
                        print('reopen file waiting for line')
                        f.close()
                        if(getattr(self,'ipDb') != None):
                            self.ipDb.close()
                        self.startTailF()
                    else:
                        empty_line_time = empty_line_time + 1
                        continue

                empty_line_time = 0
                # 保持存储集合按天分割
                totday = time.strftime("%Y_%m_%d", time.localtime(time.time()))
                self.dbCollection = 'xfb_online_%s_log' % totday

                # print('------------%s---------------->\n' % time.time())
                # print(line)
                # print('------------%s---------------->\n' % time.time())

                

                self.getRedis()
                flag = self.redis.lpush(self.list_key, line)
                print(flag)
                # self.__lineLogToMongo(line )
                # self.__lineToMongo(line)




    # log pid
    def logPid(self ,readType = 'w+'):
        f = open('readLogWorker.pid', readType)
        if readType == 'w+':
            f.write('%s' % os.getpid())
        elif readType == 'a+':
            f.write(' %s' % os.getpid())
        f.close()


    def lineLogToMongo(self ,line ):
        #####
        # nginx log format
        #'[$time_local] $host $remote_addr - "$request" '
        #'$status $body_bytes_sent "$http_referer" '
        #'"$http_user_agent" "$http_x_forwarded_for"';
        ####

        # if(re.search(r'"\n',line) == None):
        #     print('not a line')
        #     print(line)
        #     return

        line = line.strip()
        _arr = line.split(' ')

        # filter static file
        if (re.search(r'\.[js|css|png|jpg|ico|woff]', _arr[6].strip(''))):
            # print('it`s static request')
            return


        _map = {}

        request_time = _arr[0].strip('').strip('[')
        request_time.replace('[', '')

        time_int = time.mktime(time.strptime(request_time, "%d/%b/%Y:%H:%M:%S"))
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time_int)))
        mongodbCollection = time_str.split(' ')[0]
        print(mongodbCollection)

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


        ip2location = self.__ipLocation(_map['ip'])
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

        print(len(self.insertData))

        # 当满足设定的数量 则入库
        if(len(self.insertData) >= self.insertData_max_len):

            db = self.__getMongoDB(mongodbCollection)

            # try:
            #     mid = self.db.insert_many(self.insertData)
            # except AutoReconnect as e:
            #     self.db = MongoDb(self.dbName, self.dbCollection).db
            #     mid = self.db.insert_many(self.insertData)
            try:
                mid = db.insert_many(self.insertData)
            except AutoReconnect as e:
                db = self.__getMongoDB(mongodbCollection)
                mid = db.insert_many(self.insertData)


            print(mid)
            # 写入成功后清空数据列表
            self.insertData = []


    def getRedis(self):

        if (self.redis == False):
            try:
                self.redis = Redis(self.redisDbNum).db
            except BaseException as e:
                print('redis init error')

        return self.redis

    def __ipLocation(self,ip):

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

    def __getMongoDB(self ,collection):

        # totday = time.strftime("%Y_%m_%d", time.localtime(time.time()))
        # self.dbName = 'xfb'
        # self.dbCollection = 'xfb_online_%s_log' % totday
        # self.db = MongoDb(self.dbName, self.dbCollection).db

        dbCollection = 'xfb_online_%s_log' % collection
        dbName = 'xfb'
        return MongoDb(dbName, dbCollection).db


        pass



def startWatcher(logpath):
    nginxLogWatcher(logpath)

def lineToMongo(logpath):
    obj = nginxLogWatcher(logpath ,toMongo=True)

    while True:

        line = obj.getRedis().lpop(obj.list_key)
        if(not line ):
            time.sleep(0.5)
            print('wait for redis list')
            continue
        obj.lineLogToMongo(line)
    pass


if __name__ == "__main__":
    # logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\tt.log'
    # logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\xfb.log'
    # logPath = '/alidata/server/nginx/logs/xfb.log'
    # reader(logPath)

    # start_cmd = 'nohup python3 -u watcher.py -f  %s > nohup.out  2>&1 &'
    # start_cmd = 'python3  /mnt/hgfs/MyPythonProject/nginxWatcher/watcher.py -f  %s '
    # stop_cmd = 'python3 stopWatcher.py'

    try:
        commond = sys.argv[1]

        if (commond == '-f'):
            logPath = sys.argv[2]
            if(os.path.exists(logPath) == False):
                print('logpath is not exists : %s' % logPath)
            else:


                pollNum = 2
                poll = Pool(pollNum)

                for i in range(pollNum):
                    poll.apply_async(lineToMongo ,args=(logPath,))
                #
                startWatcher(logPath)
                #
                poll.close()
                poll.join()



                # watch = multiprocessing.Process(target=startWatcher ,args=(logPath,))
                # # watch.daemon = True
                # watch.start()
                #
                # # nginxLogWatcher(logPath)
                # while 1:
                #     print(watch.pid)
                #     # if(watch.is_alive() == False):
                #     print(watch.is_alive())
                #     time.sleep(2)


    except IndexError as e:
        traceback.print_exc()
        print('args error : for example \n')
        print('    python readLogpy support args : \n')
        print('    -f  /server/nginx/logs/yourlog.log \n')

