import os,time,re,traceback,sys
from DataBase.Mongo import MongoDb
from DataBase.Redis import Redis
from pymongo.errors import *
from ip2Region import Ip2Region

class reader:

    def __init__(self ,logPath):
        print('--start time : %s' % time.time())
        if(os.path.exists(logPath) == False):
            raise FileNotFoundError('日志文件路径不存在')

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
        # self.startRead()
        self.file.close()


        print('--end time : %s' % time.time())

    def startTailF(self):

        with open(self.file_path,'r+' ,newline='\n') as f:
            # 文件指针定位到文件末尾
            f.seek(0, 2)
            while True:
                line = f.readline()
                if(line == ''):
                    continue

                # print('---------------------------->\n')
                # print(line)
                # print('---------------------------->\n')
                self.__lineLogToMongo(line )
                time.sleep(0.1)

    # 记录当前 工作的 进程id
    def logPid(self ,readType = 'w+'):
        f = open('readLogWorker.pid', readType)
        if readType == 'w+':
            f.write('%s' % os.getpid())
        elif readType == 'a+':
            f.write(' %s' % os.getpid())
        f.close()

    def startRead(self):
        # self.file.readlines()
        while True:
            line = self.file.readline()

            # print('--------------%s' % self.file.tell() )
            if line == '':
                print('read end done')
                break

            # print(line)
            self.__lineLogToMongo(line)

            time.sleep(1)


    def __lineLogToMongo(self ,line ):
        #####
        # nginx log format 格式
        #'[$time_local] $host $remote_addr - "$request" '
        #'$status $body_bytes_sent "$http_referer" '
        #'"$http_user_agent" "$http_x_forwarded_for"';
        ####

        if(re.search(r'"\n',line) == None):
            print('不是完整的一行： %s' % line)
            return

        line = line.strip()
        _arr = line.split(' ')

        # 过滤掉静态文件
        try:
            if (re.search(r'\.[js|css|png|jpg|ico|woff]', _arr[6].strip(''))):
                return
        except BaseException as e:
            print('该行不匹配: %s' % line)
            return


        _map = {}

        try:
            request_time = _arr[0].strip('').strip('[')
            request_time.replace('[','')

            time_int = time.mktime(time.strptime(request_time, "%d/%b/%Y:%H:%M:%S"))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time_int)))
        except BaseException as e:
            traceback.print_exc()
            print(_arr[0])
            print('该行时间不匹配: %s' % line)
            return

        try:
            _map['status'] = _arr[8].strip('')
        except BaseException as e:
            pre_line = self.redis.get('pre_line')
            print(pre_line + line)
            print('status 匹配错误')
            print(line)
            print(_arr)
            _map['status'] = '0'
            return


        try:
            _map['content_size'] = _arr[9].strip('')
        except BaseException as e:
            pre_line = self.redis.get('pre_line')
            print(pre_line + line)
            print('content_size 匹配失败')
            _map['content_size'] = ''
            return


        try:
            _map['referer'] = _arr[10].strip('').strip('"')
        except BaseException as e:
            pre_line = self.redis.get('pre_line')
            print(pre_line + line)
            print('refere 匹配失败')
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



        # 后面的部分

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



if __name__ == "__main__":
    # logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\tt.log'
    # logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\xfb.log'
    # logPath = '/alidata/server/nginx/logs/xfb.log'
    # reader(logPath)

    try:
        commond = sys.argv[1]
        if (commond == '-f'):
            logPath = sys.argv[2]
            if(os.path.exists(logPath) == False):
                print('logpath is not exists : %s' % logPath)
            else:
                reader(logPath)

    except IndexError as e:
        print('args error : for example \n')
        print('    python readLogpy support args : \n')
        print('    -f  /server/nginx/logs/yourlog.log \n')

