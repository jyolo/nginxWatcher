import os,sys,time,traceback,re,signal
from redis import Redis as RedisClient,exceptions as redisExceptions
from multiprocessing import Pool,Pipe,Manager

# 处理ctrl+c 进程的退出
def _BeKill(signalnum, frame):
    print(signalnum)
    sys.exit()

# 记录当前 工作的 进程id
def logPid(readType = 'w+'):
    f = open('worker.pid' ,readType)
    if readType == 'w+':
        f.write('%s' % os.getpid())
    elif readType == 'a+':
        f.write(' %s' % os.getpid())
        
    f.close()

#将10位时间戳转换为时间字符串，默认为2017-10-01 13:37:04格式 
def timestamp_to_date(format_string="%Y-%m-%d %H:%M:%S" ,time_stamp = time.time() ): 
    time_array = time.localtime(time_stamp) 
    str_date = time.strftime(format_string, time_array) 
    return str_date


class LogWather(object):

    def __init__(self ,filePath):
        if os.path.exists(filePath) == False:
            raise FileNotFoundError("%s 文件不存在" % filePath);
        if os.path.isfile(filePath) == False:
            raise FileNotFoundError("%s 请指定该目录的文件" % filePath)
        
        self.file = filePath
        # redis
        self.redis = False
        self.redisConfig = {
            "host": "127.0.0.1",
            "port": 6379,
            "auth": "",
            'db': 10
        }


        logPid()

        nowDate = timestamp_to_date("%Y_%m_%d")
        
        # redis key 的前缀
        self.keyPrefix = nowDate +'_'+ filePath.split('/').pop().replace('.','_')
        
        
        self.UnNormalRedisKey = '%s_UnNormalIp' % self.keyPrefix # 判定为 非正常请求次数的ip
        self.robotRedisKey = '%s_robotIp' % self.keyPrefix # 爬虫/采集机器人 ip 存放redis key
        
        # step1 分析日志.
        self.betweenRequestTime= 60  # 日志中的请求间隔时间 单位秒
        self.ntopLimit = 60 # 从日志中在指定时间内取出多少条 请求次数最多的ip
        self.checkTimeLimit= 60      # 多长时间检测一次 非正常请求次数的ip

        self.ignoreRequestType = ['js','css','png' ,'jpg','jpeg','ico','gif','woff'] # 忽略的请求类型
        # 判断阀值
        self.unnormalRequestTImes= 30  # 判断是否是超频请求的基准次数 在nginx日志中每分钟内超过多少次才判定为超频请求
        self.overRequestProcent = 0.65 # 满足 超频请求率 判断阀值  [ 每分钟超过阀值的请求次数（每分钟）  / 总的请求次数（每分钟） ]
        self.unnormalRequestPage = 0.2 # 满足 不合格的相同页面的请求率 判断阀值  [请求不同的页面数量 / 本次超频的总请求数]
        self.robotPercent = 0.5 # 满足 机器人几率 判断阀值  [不合格的相同页面的请求率 / 总的超频请求次数 ]

    # 获取redis实例          
    def getRedis(self):
        if self.redis == False:
            self.redis = RedisClient(
                host = self.redisConfig['host'],
                port = self.redisConfig['port'],
                password = self.redisConfig['auth'],
                db = self.redisConfig['db'],
                decode_responses = True
            )
            return self.redis
        else:
            return self.redis
        

    # 获取统计命令
    def getCountCmd(self ,typeIndex = 0 ,startTime = False ,endTime = False ):
        
        # 不带时间区间的统计
        if startTime == False and endTime == False:
            cmd = [
                # 统计某个时间段 ` 请求次数 ip ` 倒序排序 
                "awk '{print $4}' %s | sort | uniq -c | sort -nr | head -n %s" % (self.file ,self.ntopLimit) ,
                # 统计某个时间段内  所有 ip 请求的 详情 
                "awk '{print $4 , $7 , $8 , $9 }' %s | sort | uniq -c | sort -nr | head -n %s" % (self.file,self.ntopLimit)
            ]

        else:
            cmd = [
                # 统计某个时间段 ` 请求次数 ip ` 倒序排序 
                "awk '$1>=\"[%s\" && $1<=\"[%s\" {print $4}' %s | sort | uniq -c | sort -nr | head -n %s" % (startTime,endTime,self.file,self.ntopLimit) ,
                # 统计某个时间段内  所有 ip 请求的 详情 
                "awk '$1>=\"[%s\" && $1<=\"[%s\" {print $4 , $7 , $8 , $9 }' %s | sort | uniq -c | sort -nr | head -n %s" % (startTime,endTime,self.file,self.ntopLimit)
            ] 

        # 线上格式和我本地不一致的时候 注意 $变量 的位置
        # awk '$1>="[08/May/2019:17:17:45" && $1<="[08/May/2019:17:17:45" {print $4}' ./access.log | sort | uniq -c | sort -nr | head -n 10
        # awk '$1>="[08/May/2019:17:17:45" && $1<="[08/May/2019:17:17:45" {print $4 ',' $7 ',' $8}' ./access.log | sort | uniq -c | sort -nr | head -n 10
        
        return cmd[typeIndex]


    # 检测的时间间隔 ,每隔多少秒检测一次   
    def StartWatcher(self ,cmdTtype = 0  ):
        try:
            logPid('a+')

            while True:
                print('---start watcher pid: %s ---at: %s' % (os.getpid(),timestamp_to_date()))

                start_time = time.strftime('%d/%b/%Y:%H:%M:%S',time.localtime(time.time() - self.betweenRequestTime))
                end_time =  time.strftime('%d/%b/%Y:%H:%M:%S',time.localtime(time.time() ))
                
                stime = start_time.replace('15/','11/')
                etime = end_time.replace('15/','11/')

                
                # stime = start_time
                # etime = end_time
                print('------------开始检查 %s - %s 时间区间里请求最高的前十位 IP------------' % ( etime ,stime))
                # stime = time.strftime('[%d/%b/%Y:%H:%M:%S',time.localtime(time.time() - self.betweenRequestTime))
                # etime = time.strftime('[%d/%b/%Y:%H:%M:%S',time.localtime(time.time() ))
                # stime = '09/May/2019:10:03:00'
                # etime = '09/May/2019:10:03:59'
                

                # 按日期分割日志
                # os.popen('cat %s | egrep "17/Jul/2019" | sed  -n "/00:00:00/,/23:59:59/p" > /tmp/17.log' % self.file)

                # 执行统计命令
                cmd = self.getCountCmd(cmdTtype ,startTime=stime ,endTime=etime )
                # print(cmd)
                f = os.popen(cmd).read()

                # 有数据的时候
                if f.strip() != '':

                    data = f.strip().split("\n")
                    
                    _count = []
                    for i in data:
                        strList = i.strip(' ').split(' ')
                        ###
                        # 第一个过滤 每分钟超出 请求阀值的 丢入到 待检测队列中
                        ###
                        if int(strList[0]) > self.unnormalRequestTImes:
                            print('IP: %s in limit time request total : %s times' % (strList[1] ,strList[0] ) )
                            self.getRedis().lpush(self.UnNormalRedisKey ,strList[1])
                        else:
                            continue
                else:
                    print('---between stime %s - etime %s 暂无请求日志  ' % (stime,etime) )


                print('---end watcher pid: %s ---at: %s' % (os.getpid(),timestamp_to_date()))
                time.sleep(self.checkTimeLimit)
                

        except BaseException as e:
            traceback.print_exc()
            sys.exit()
            
    
    # 过滤掉忽略的静态请求链接
    def filtterStaticRequest(self,MapData):
        _compile = []
        
        for c in self.ignoreRequestType:
            _compile.append( re.compile(r'(\.%s)(\?\S+)?' % c,re.I) )
            # print(re.compile(r'\.(%s)(\?\S+)?' % c,re.I).findall('/pc/lib/layui/css/modules/layer/default/layer.css?v=3.1.0'))

        def regMatch(_str):
            for pattern in _compile:
                _match = pattern.findall(_str)
                if len(_match) :
                    return True
                else:
                    continue
            return False

        _return = {}
        for k in MapData:
            arr = []
            for index,page in enumerate(MapData[k]):
               
                if regMatch(page) == False:
                    arr.append(page)
            

            if len(arr) :
                _return[k] = arr
            
        if len(_return) == 0:
            return {}
        else:
            return _return


    def RequestWatcher(self):
        try:
            logPid('a+')
            print('---start RequestWatcher pid: %s ---at: %s' % (os.getpid(),timestamp_to_date()) ,end="\n")
            while True:
                
                ip = self.getRedis().lpop(self.UnNormalRedisKey)
                if ip == None:
                    # print('RequestWatcher pid: %s waitting' % (os.getpid()) ,end="\n")
                    # 没有ip 的时候 休息1秒 然后 继续
                    time.sleep(1)
                    continue

                # ip = '211.99.16.98'
                # ip = '36.17.90.240'
                # ip = '119.137.55.242'
                # ip = '60.191.61.151'
                # ip = '113.249.53.211'
                # ip = '112.245.244.30'
                print('handle by pid: %s ; current IP: %s' % (os.getpid() ,ip))

                # cmd = 'cat %s | egrep %s' % (self.file ,ip)
                cmd = "awk '$4==\"%s\" {print $1, $7 ,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27 }' %s | sort -r" % (ip,self.file )

                #print(cmd)
                f = os.popen(cmd).read()

                
                
                _list = f.strip().split("\n")
                
                ipRequsetLogKey = '%s_ipRequestLog:%s' % (self.keyPrefix,ip)
                ttl = 86400 # 过期时间 一天

                item = {}
                for i in _list:
                    
                    self.getRedis().lpush(ipRequsetLogKey , i )
                    self.getRedis().expire(ipRequsetLogKey ,ttl)
                    
                    _arg = i.strip().split(' ')
                    _time = _arg[0].lstrip('[')
                    
                    minute = ''.join( _time.split(':')[1:3])
                    # print(_time.split(':'));
                    
                    item[minute] = []
                    for j in _list:
                        _sub_arg = j.strip().split(' ')
                        _sub_time = _sub_arg[0].lstrip('[')
                        sub_minute = ''.join( _sub_time.split(':')[1:3])
                        
                        if  sub_minute == minute:
                           
                            # /数字 全部替换成 /[ID]
                            if re.findall(r'\/\d+' ,_sub_arg[1]) :
                                _requestUrl = re.sub(r'\/\d+','/[ID]',_sub_arg[1])
                            else:
                                _requestUrl = _sub_arg[1]

                            # 每分钟的所有请求
                            item[minute].append(_requestUrl)
                        else:
                            continue
                        
                # 过滤掉 静态文件文件的请求
                item = self.filtterStaticRequest(item)
                
                if len(item) == 0:
                    print('ip:%s ; 过滤掉静态文件的请求后，不满足超频请求率 单位时间请求次数： %s' % (ip,len(item) ) )
                    continue

                # 截至检测的时间 该ip的所有请求 以分钟为单为 分割成 数组
                total_minute_visited = len(item)  
                overTime = 0
                
                # 一分钟内超过可疑请求频率的集合 （超频请求）
                highRequestMinute = {}
                for k in item:
                    ###
                    # 第二个过滤 在所有分钟请求次数中 过滤出 超出 阀值的 不正常的请求
                    ###
                    if len(item[k]) >= self.unnormalRequestTImes:
                        overTime = overTime+1
                        highRequestMinute[k] = item[k]
                    

                ###
                # 第三个过滤 计算出该 ip的 超频请求率
                # 超频请求率
                # 第一个算法 [ 每分钟超过阀值的请求次数（每分钟）  / 总的 请求次数（每分钟）] 一个暴力采集的ip能达到 0.75  该值越高 越暴力
                ###
                print('超频请求次数 ：%s 总的请求次数/每分钟： %s ' % (overTime , total_minute_visited))
                over_request_procent = float('%.2f' % (overTime / total_minute_visited))
                print("ip:%s ; 超频请求率： %s \n" % (ip,over_request_procent))

                
                if over_request_procent >= self.overRequestProcent:
                    
                     # 忽略 / 剔除 掉静态文件的请求
                    highRequestMinute = self.filtterStaticRequest(highRequestMinute)
                    if len(highRequestMinute) == 0:
                        print('ip:%s ; 不满足请求页码合格率' % (ip ))
                        continue
                    
                    page_percent = []
                    for k,v in enumerate(highRequestMinute):
                        
                        # 超出阀值频率的 请求总次数
                        overRequestTime = len(highRequestMinute[v])
                        page_count = []
                        for p in highRequestMinute[v]:
                            t = highRequestMinute[v].count(p)
                            if t not in page_count:
                                page_count.append(t) 
                        
                        # 在超频请求中 一共请求了 多少个不同的页面
                        samePageRequestTimes = len(page_count)
                        ###
                        # 不合格的相同页面的请求率 在超频请求中 计算 每个超频请求的同样页面的百分比  该值越低  越是采集器    请求不同的页面数量 / 本次超频的总请求数 
                        ###
                        percent = float('%.2f' % (samePageRequestTimes / overRequestTime))
                        print( "ip:%s ; 超频请求时间： %s ; 相同页面请求率：%s " %(ip,(v[0:2] + ':' + v[2:]) ,percent) )
                        if percent <= self.unnormalRequestPage :
                            page_percent.append(percent)
                        
                    print('ip:%s ;总超频请求次数：%s ;不合格的页面请求率的总次数: %s' % (ip ,len(highRequestMinute) ,len(page_percent)))
                    ########
                    # 机器人/爬虫 几率 = 不合格的相同页面的请求率 / 总的超频请求次数  
                    ####### 
                    RobotPercent = float('%.2f' % (len(page_percent) / len(highRequestMinute)))
                    
                    if RobotPercent >= self.robotPercent:
                        score = self.getRedis().zscore(self.robotRedisKey ,ip)
                        if score == None:
                            print('该ip:%s 机器人判断率初始化' % (ip) )
                            self.getRedis().zadd(self.robotRedisKey ,{ip:1})
                        else:
                            print('该ip:%s 机器人判断率 + 1' % (ip) )
                            self.getRedis().zincrby(self.robotRedisKey ,1,ip)

                   
                     # 这里的分数指的是 在每分钟的检查中 每一轮都检查出 该ip ，则该ipo的 可疑度 + 1

                # 释放变量
                del item 
                del _list
        
            print('---end RequestWatcher pid: %s ---at: %s' % (os.getpid(),timestamp_to_date()))

        except Exception as e:
            traceback.print_exc()
            sys.exit()




# 开始
def watch(logPath = '/www/wwwlogs/xfb.log'):
   
    try:
        # 捕获ctrl+c 的信号量
        signal.signal(signal.SIGINT ,_BeKill)
        signal.signal(signal.SIGTERM, _BeKill)
        
        obj = LogWather(logPath)


        poolNum = 2
        
        p = Pool(poolNum)
        
        for i in range(poolNum):
            if i == 0 :
                p.apply_async(obj.StartWatcher)
            else:
                p.apply_async(obj.RequestWatcher)


        p.close()
        p.join()
        

    except Exception as e:
        print('zzz')
        traceback.print_exc()
        sys.exit()
    

if __name__ == "__main__":
    
    
    
    try:
        
        action = sys.argv[1]
        if callable(eval(action)) == True:
            if os.path.exists(sys.argv[2]) == False:
                raise FileNotFoundError()

            eval(sys.argv[1])(sys.argv[2])
                

   
    except IndexError as e :
        print('不支持该参数')
    except FileNotFoundError as e:
        print('日志文件不存在 请检查日志的路径')
    

           
    