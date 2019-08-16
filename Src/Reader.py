import time,re,traceback,os,sys
from Src.Base import Base,tail_call_optimized
from redis.exceptions import RedisError


class Reader(Base):


    @tail_call_optimized
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
                        print('入队成功　%s' % flag)

                    """
                    文件没有内容的时候　不进入　for in 中　则　raise StopIteration　错误　
                    循环尝试超过　指定次数后　则关闭文件从新打开文件
                    """
                    raise StopIteration('暂无数据')

                except StopIteration as e:
                    emptyTimes = emptyTimes + 1

                    if(emptyTimes >= self.emptyLineMaxTime):
                        print('empty line %s time' % emptyTimes)
                        time.sleep(1)
                        f.close()
                        print('关闭文件重新读取文件')
                        return self.startTailf()
                    else:
                        time.sleep(1)
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

                # except Exception as e:
                #     # 其它未知错误　直接退出
                #     traceback.print_exc()
                #     exit(0)
