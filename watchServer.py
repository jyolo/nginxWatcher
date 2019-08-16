import os,sys
from src.Reader import Reader
from src.Writer import Writer


def read(logPath):
    Reader(logPath).startTailf()

def write(logFileName ,withStatic):

    Writer(logFileName).start(withStatic)

if __name__ == '__main__':
    commond = sys.argv

    print(commond)

    # os.popen('nohup python3 -u watcher.py -f /www/wwwlogs/local.test.com.log -m read > read.out  2>&1 &')
    # print('success')

