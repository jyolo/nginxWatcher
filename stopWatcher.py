import os,sys,traceback,re

if __name__ == "__main__":
    try:
        res = os.popen('ps -aux | grep watcher.py')

        pids = []
        for i in res:
            if(i.find('-u') > 0):
                print(i)
                obj = re.search(r'root\s+(\d+)' ,i )
                pid = obj.groups()[0]
                pids.append(pid)

        if(len(pids)):
            for p in pids:
                res = os.popen('kill %s' % p)
                if(res):
                    print('kill %s success' % p)

        else:
            print('not found python ro run watcher.py script')

    except BaseException as e:
        traceback.print_exc()
        print('watcher server stop fail')
        exit()



