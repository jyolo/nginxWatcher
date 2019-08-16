import sys
from multiprocessing import Pool
from Src.Reader import Reader
from Src.Writer import Writer


class runner:
    def __init__(self ,cmds):
        print(cmds)

        func = (hasattr(self, cmds['runModel']))

        if(func == False):
            print('-m　只支持　read 或者　write')
            return

        self.cmds = cmds


        self.__getattribute__(cmds['runModel'])()


    def read(self ):
        Reader(
            logPath = self.cmds['logPath'],
            redisKey = self.cmds['redisKey'],
        ).startTailf()

    def write(self):
        Writer(
            redisKey = self.cmds['redisKey'],
            withStatic = self.cmds['withStatic']
        ).start()





def formCommands(cmdArgs):
    _map = {
        'logPath':None,
        'redieKey':None,
        'runModel':None,
        'proccessNum':2,
        'withStatic':0,
    }

    # log　file path
    if ('-f' in cmdArgs):
        _map['logPath'] = cmdArgs[cmdArgs.index('-f') + 1].strip()

    # redis key name
    if ('-k' in cmdArgs):
        _map['redisKey'] = cmdArgs[cmdArgs.index('-k') + 1].strip()

    # run model
    if ('-m' in cmdArgs):
        _map['runModel'] = cmdArgs[cmdArgs.index('-m') + 1].strip()

    # write model proccess number
    if ('-p' in cmdArgs):
        _map['proccessNum'] = int(cmdArgs[cmdArgs.index('-p') + 1].strip())

    if ('-with-static' in cmdArgs):
        _map['withStatic'] = 1

    return _map

if __name__ == '__main__':
    commond = sys.argv

    # print(commond)
    # print('-----------------------------------doc----------------------------------- ')
    # print('| args  : ')
    # print('|    support args : ')
    # print('|    -f  your access.log path  ')
    # print('|    -m  run model -m [read | write | both]  ')
    # print('|    -p  writer Proccess Number  ')
    # print('|    -with-static  writer Proccess will not filter static file request  ')
    # print('| only read log; for example: python3 -u watcher.py -f  /wwwlogs/access.log -m read   ')
    # print('| only write log; for example: python3 -u watcher.py -f  /wwwlogs/access.log -m write -p 4   ')
    # print('| read and write log; for example: python3 -u watcher.py -f  /wwwlogs/access.log [ -m both -p 2]   ')
    # print('-----------------------------------doc----------------------------------- ')

    args = formCommands(commond)

    runModel = args['runModel']

    if runModel == 'write':
        
        poolNum = args['proccessNum']
        pool = Pool(poolNum)
        for i in range(poolNum):
            pool.apply_async(runner, args=(args,))
        pool.close()
        pool.join()

    else:
        runner(args)


    # cmd = 'nohup python3 -u watcher.py -f %s -m %s > ./Log/%s.out  2>&1 &' % (logPath ,runmodel ,runmodel)


    # print(cmd)
    # os.popen(cmd)
    # print('success')

