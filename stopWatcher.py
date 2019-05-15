import os,sys

if __name__ == "__main__":
    try:
        f = open('worker.pid' ,'r+')
        pid = f.read()
        os.popen('kill -9 %s' % pid)
        print('watcher server stopped')
    except BaseException as e:
        print('停止失败')
    