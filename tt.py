import os,time
from requests import request

if __name__ == "__main__":
    # read_logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\xfb.log'
    # with open(read_logPath) as read_file :
    #     while 1:
    #
    #         line = read_file.readline()
    #         print(line)
    #         write_logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\tt.log'
    #         write_file = open(write_logPath,'a+',buffering=1)
    #         write_file.seek(0,2)
    #         # while 1:
    #         # write_file.write('[26/Jul/2019:04:00:15 +0800] n.xfb315.com 120.43.110.133 - "GET /complaints/details/94314934 HTTP/1.1" 200 3625 "https://www.baidu.com/s?wd=%e4%ba%91%e7%ab%af%e5%95%86%e5%8a%a1" "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.89 Safari/537.36 UCBrowser/11.6.8.952" "-"' + '\n')
    #         write_file.write(line)
    #         # print(line)
    #         write_file.flush()
    #         print('append')
    #         time.sleep(0.1)


    interval = 0
    while 1:
        target1 = 'http://local.test.com/?time=%s' % time.time()
        target2 = 'http://local.jump.com/?time=%s' % time.time()

        res = request(method='get', url=target1)
        res = request(method='get', url=target2)
        # interval = interval + 1
        # if interval >= 1:
        #     time.sleep(2)
        print(res)
        # time.sleep(1)