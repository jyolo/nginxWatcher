import os,time


if __name__ == "__main__":
    logPath = 'G:\\MyPythonProject\\nginxWatcher\\log\\tt.log'
    file = open(logPath,'a+',buffering=1)
    file.seek(0,2)
    while 1:
        line = file.write('[26/Jul/2019:04:00:15 +0800] n.xfb315.com 120.43.110.133 - "GET /complaints/details/94314934 HTTP/1.1" 200 3625 "https://www.baidu.com/s?wd=%e4%ba%91%e7%ab%af%e5%95%86%e5%8a%a1" "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.89 Safari/537.36 UCBrowser/11.6.8.952" "-"' + '\n')
        # print(line)
        file.flush()
        print('append')