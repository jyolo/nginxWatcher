import time,re,os
from Src.Base import Base
from redis.exceptions import RedisError
from pymongo.errors import PyMongoError


class Writer(Base):


    def start(self ):
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

                self.lineLogToMongo(line )
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


    def lineLogToMongo(self ,line ):
        #####
        # nginx log format
        #'[$time_local] $host $remote_addr - "$request" '
        #'$status $body_bytes_sent "$http_referer" '
        #'"$http_user_agent" "$http_x_forwarded_for"';
        ####

        line = line.strip()
        _arr = line.split(' ')


        # filter static file 如果　-static 则　withStatic = True
        if(self.withStatic == False):
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

