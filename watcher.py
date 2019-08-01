import os,time,re,traceback,sys,subprocess
import multiprocessing
from DataBase.Mongo import MongoDb
from pymongo.errors import *
from ip2Region import Ip2Region

class nginxLogWatcher:

    def __init__(self ,logPath):
        print('--start time : %s' % time.time())
        if(os.path.exists(logPath) == False):
            raise FileNotFoundError('logfile is not exsits')

        totday  = time.strftime("%d", time.localtime(time.time()))

        self.dbName = 'xfb'
        self.dbCollection = 'xfb_online_%s_log' % totday
        self.db = MongoDb(self.dbName, self.dbCollection).db


        self.logPid()
        self.file_path = logPath;
        self.file = open(logPath ,newline='\n')


        self.insertData = []
        self.insertData_max_len = 50

        self.startTailF()
        self.file.close()



    def startTailF(self ,cmd = ''):

        with open(self.file_path,'r+' ,newline='\n') as f:

            f.seek(0, 2)
            # 当文件被切割或者文件被修改过后 由于 文件指针已经被改变 会始终读取不到数据
            # empty_line_time 为计数器，当始终无法获取数据 超过一定次数 则关闭文件句柄 从新
            # 打开文件 并把指针指向文件末尾从新读取文件
            # 计数器 可根据网站流量
            empty_line_time = 0
            while True:
                time.sleep(0.1)
                line = f.readline()

                # 当前获取不到记录的时候 把文件指针 指向文件头部
                if(line == ''):
                    print('# 读到空行%s数' % empty_line_time)
                    time.sleep(0.5)
                    if empty_line_time >= 2:
                        print('reopen file waiting for line')
                        f.close()
                        self.startTailF()
                    else:
                        empty_line_time = empty_line_time + 1
                    continue

                empty_line_time = 0


                # print('---------------------------->\n')
                # print(line)
                # print('---------------------------->\n')
                self.__lineLogToMongo(line )


    # log pid
    def logPid(self ,readType = 'w+'):
        f = open('readLogWorker.pid', readType)
        if readType == 'w+':
            f.write('%s' % os.getpid())
        elif readType == 'a+':
            f.write(' %s' % os.getpid())
        f.close()


    def __lineLogToMongo(self ,line ):
        #####
        # nginx log format
        #'[$time_local] $host $remote_addr - "$request" '
        #'$status $body_bytes_sent "$http_referer" '
        #'"$http_user_agent" "$http_x_forwarded_for"';
        ####

        if(re.search(r'"\n',line) == None):
            print('not a line')
            print(line)
            return 

        line = line.strip()
        _arr = line.split(' ')

        # filter static file
        try:
            if (re.search(r'\.[js|css|png|jpg|ico|woff]', _arr[6].strip(''))):
                return
        except BaseException as e:
            print('not match static file: %s' % line)
            exit()


        _map = {}

        try:
            request_time = _arr[0].strip('').strip('[')
            request_time.replace('[','')

            time_int = time.mktime(time.strptime(request_time, "%d/%b/%Y:%H:%M:%S"))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time_int)))
        except BaseException as e:
            traceback.print_exc()
            print(_arr[0])
            print('not match time: %s' % line)
            exit()

        try:
            _map['status'] = _arr[8].strip('')
        except BaseException as e:
            print('status match error')
            print(line)
            print(_arr)
            _map['status'] = '0'
            exit()


        try:
            _map['content_size'] = _arr[9].strip('')
        except BaseException as e:
            print('content_size match error')
            _map['content_size'] = ''
            return


        try:
            _map['referer'] = _arr[10].strip('').strip('"')
        except BaseException as e:
            print('refere match error')
            _map['referer'] = '-'
            return

        _map['time_str'] = time_str
        _map['time_int'] = int(time_int)
        _map['web_site'] = _arr[2].strip('')
        _map['ip'] = _arr[3].strip('')
        ip2location = self.__ipLocation(_map['ip'])

        if (ip2location != False):
            _map['country'] = ip2location[0]
            _map['region'] = ip2location[1]
            _map['province'] = ip2location[2]
            _map['city'] = ip2location[3]
            _map['isp'] = ip2location[4]
        else:
            _map['country'] = 0
            _map['region'] = 0
            _map['province'] = 0
            _map['city'] = 0
            _map['isp'] = 0

        _map['method'] = _arr[5].strip('').strip('"')
        _map['url'] = _arr[6].strip('')



        # ua and x_forward_for

        last_part = line.split(' "')

        _map['user_agent'] = last_part[-2].strip('"')
        _map['http_x_forwarded_for'] = last_part[-1].strip('"')


        if(re.search(r'-',_map['http_x_forwarded_for'])):
            _map['http_x_forwarded_for'] = _map['http_x_forwarded_for'].strip('"')
        else:
            iplist = _map['http_x_forwarded_for'].split(',')
            x_iplist = ''
            for i in iplist:
                x_ip = i.strip()
                ip_result = self.ipDb.binarySearch(x_ip)
                location = ip_result['region'].decode('utf-8')
                x_iplist += '%s,%s' % (x_ip ,location) + '->'
            _map['http_x_forwarded_for'] = x_iplist.strip('->')



        self.insertData.append(_map)
        print(len(self.insertData))
        if(len(self.insertData) >= self.insertData_max_len):
            try:
                mid = self.db.insert_many(self.insertData)
            except AutoReconnect as e:
                self.db = MongoDb(self.dbName, self.dbCollection).db
                mid = self.db.insert_many(self.insertData)

            print(mid)
            self.insertData = []


    def __ipLocation(self,ip):
        try:
            ipDbPath = './ip2region.db'
            self.ipDb = Ip2Region(ipDbPath)
            ip_result = self.ipDb.binarySearch(ip)
            location = ip_result['region'].decode('utf-8').split('|')

            return location

        except OSError as e:
            traceback.print_exc()
            return False
        except SyntaxError as e:
            traceback.print_exc()
            return False
        except BaseException as e:
            traceback.print_exc()
            return  False




def startWatcher(logpath):
    nginxLogWatcher(logpath)



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
                startWatcher(logPath)
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

