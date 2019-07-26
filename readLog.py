import os,time,re,traceback
from DataBase.Mongo import MongoDb
from pymongo.errors import *
from ip2Region import Ip2Region

class reader:

    def __init__(self ,logPath):
        print('--start time : %s' % time.time())
        if(os.path.exists(logPath) == False):
            raise FileNotFoundError('日志文件路径不存在')

        self.logPid()
        self.file_path = logPath;
        self.file = open(logPath)
        self.db = MongoDb('xfb','xfb_online_log').db
        self.insertData = []
        self.insertData_max_len = 50

        self.startTailF()
        # self.startRead()
        self.file.close()


        print('--end time : %s' % time.time())

    def startTailF(self):

        with open(self.file_path,'r+') as f:
            # 文件指针定位到文件末尾
            f.seek(0, 2)
            while True:
                line = f.readline()
                if(line == ''):
                    continue
                self.__lineLogToMongo(line)

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


            print(line)
            self.__lineLogToMongo(line)

    def __lineLogToMongo(self ,line):
        _arr = line.split(' ')
        # 过滤掉静态文件
        try:
            if (re.search(r'\.[js|css|png|jpg|ico]', _arr[6].strip(''))):
                return
        except Exception as e:
            print('该行不匹配: %s' % line)
            return


        _map = {}

        try:
            request_time = _arr[0].strip('[')
            time_int = time.mktime(time.strptime(int(request_time), "%d/%b/%Y:%H:%M:%S"))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time_int)))
        except Exception as e:
            print('该行时间不匹配: %s' % line)
            print(_arr)
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
        _map['status'] = _arr[8].strip('')
        _map['content_size'] = _arr[9].strip('')
        _map['referer'] = _arr[10].strip('').strip('"')
        _map['user_agent'] = ' '.join(_arr[11:-2]).strip(' ').strip('"')


        self.insertData.append(_map)
        print(len(self.insertData))
        if(len(self.insertData) >= self.insertData_max_len):
            try:
                mid = self.db.insert_many(self.insertData)
            except AutoReconnect as e:
                self.db = MongoDb('xfb', 'access_log').db
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
        except Exception as e:
            traceback.print_exc()
            return  False



if __name__ == "__main__":
    # logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\xfb.log'
    logPath = '/alidata/server/nginx/logs/xfb.log'
    reader(logPath)
