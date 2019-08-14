import os,time,re,traceback,os,fcntl
from multiprocessing import Pool,Manager,Process,Queue,Pipe
from multiprocessing.connection import Listener,Client
from DataBase.Mongo import MongoDb
from DataBase.Redis import Redis
from pymongo.errors import *
from ip2Region import Ip2Region

class nginxLogWatcher:

    def __init__(self ,logPath ):
        print('--start time : %s' % time.time())
        if(os.path.exists(logPath) == False):
            raise FileNotFoundError('logfile is not exsits')




        # self.logPid()
        self.file_path = logPath
        self.ipDb = None
        self.redisDbNum = 3
        self.list_key = 'nginx_log'
        self.redis = False


        self.insertData = []
        self.insertData_max_len = 50




    #  45474
    #  1829130

    def startTailF2(self):
        # 关闭　输出端　只　输入
        try:
            address = ('127.0.0.1', 6000)  # family is deduced to be 'AF_INET'
            listener = Listener(address)

            conn = listener.accept()




        except BaseException as e:
            traceback.print_exc()
            print('BaseException')



        empty_line_time = 0
        with open(self.file_path ,newline="\n") as f:
            f.seek(0,2)
            while 1:
                time.sleep(0.01)
                try:
                    for line in f:
                        empty_line_time = 0

                        conn.send(line)
                        # res = self.queue.get()
                        # print(res)
                    # print(self.queue.full())
                    # 流式读取之后就　无数据就　raise StopIteration

                    raise StopIteration('暂无数据')

                except StopIteration  as e :
                    empty_line_time = empty_line_time + 1
                    print('pid : %s waiting for logs %s time'  % (os.getpid() ,empty_line_time))
                    time.sleep(1)
                    # 连续10次没有读到数据　则释放文件句柄　重启该方法
                    if(empty_line_time > 10):
                        f.close()
                        conn.close()
                        listener.close()
                        self.startTailF2()

                except BaseException as e:
                    traceback.print_exc()
                    f.close()
                    conn.close()
                    listener.close()
                    exit(0)




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

        print('pid:%s  %s ---- %s' % (os.getpid(),mongodbCollection ,len(self.insertData)) )

        # 当满足设定的数量 则入库
        if(len(self.insertData) >= self.insertData_max_len):

            db = self.__getMongoDB(mongodbCollection)

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
        return MongoDb(dbName, dbCollection ).db


        pass



def startWatcher(log_path ):
    try:
        nginxLogWatcher(log_path).startTailF2()
    except BaseException as e:
        traceback.print_exc()
        print('startWtcher Error')
        exit(0)



def lineToMongo(log_path ):
    conn = False
    # 新对象　用于双线程　pop　队列中的数据　入库
    obj = nginxLogWatcher(log_path)

    while 1:
        try:
            if(conn == False):
                address = ('127.0.0.1', 6000)
                conn = Client(address)
                print(conn)


            line = conn.recv()
            print('pid: %s recv:-- %s' % (os.getpid() ,line) )
            # obj.lineLogToMongo(line)


        except Exception as e:
            # traceback.print_exc()
            print('lineToMongo--> pid : %s 尝试重新链接链接' % os.getpid())
            time.sleep(1)
            conn.close()
            lineToMongo(log_path)


    return


    # 新对象　用于双线程　pop　队列中的数据　入库
    obj = nginxLogWatcher(log_path)



    while 1:

        try:

            line = conn.recv()
            print(line)

        except BaseException as e:

            time.sleep(2)
            conn.close()
            print('－－－－－pid: %s wait for data' % os.getpid())
            lineToMongo(log_path)






def badIpChecker():
    while 1:
        time.sleep(3)
        print('badIpChecker-----111111111111111111')


# log pid
def logPid(readType = 'w+'):
    try:
        f = open('readLogWorker.pid', readType)
        fcntl.flock(f, fcntl.LOCK_EX)
        if readType == 'w+':
            f.write('%s' % os.getpid())
        elif readType == 'a+':
            f.write('\n%s' % os.getpid())
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

        return True
    except IOError as e:
        print('locked')








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

                # queue = Queue(1024 * 100)
                #
                # p1 = Process(target=badIpChecker )
                # p2 = Process(target=lineToMongo ,args=(logPath,queue, ))
                #
                # p1.start()
                # p2.start()
                #
                # startWatcher(logPath, queue)
                #
                # p1.join()
                # p2.join()





                pollNum = 3
                poll = Pool(pollNum)

                # for i in range(pollNum):
                # 读取日志　send
                poll.apply_async(startWatcher ,args=(logPath,))
                # 接收line
                poll.apply_async(lineToMongo, args=(logPath,))
                poll.apply_async(lineToMongo, args=(logPath,))



                poll.close()
                poll.join()




    except IndexError as e:
        traceback.print_exc()
        print('args error : for example \n')
        print('    python readLogpy support args : \n')
        print('    -f  /server/nginx/logs/yourlog.log \n')

