import sys,traceback
from multiprocessing import Pool
from Src.Reader import Reader
from Src.Writer import Writer


class runner:
    def __init__(self ,cmds):


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
        _map['runModel'] = 'read'

    # redis key name
    if ('-k' in cmdArgs):
        _map['redisKey'] = cmdArgs[cmdArgs.index('-k') + 1].strip()

    # run model
    if ('-m' in cmdArgs):
        _map['runModel'] = cmdArgs[cmdArgs.index('-m') + 1].strip()

    # write model proccess number
    if ('-p' in cmdArgs):
        _map['proccessNum'] = int(cmdArgs[cmdArgs.index('-p') + 1].strip())
        _map['runModel'] = 'write'

    if ('-with-static' in cmdArgs):
        _map['withStatic'] = 1

    return _map

if __name__ == '__main__':
    commond = sys.argv

    """
    参数说明  : 
        -f  your access.log path  
        -k  your redis key name  
        -m  run model -m [read | write]  
        -p  writer model Proccess Number defualt 2
        -with-static  writer model Proccess will not filter static file request
    read model example:
        python3 watcher.py -k access_log_80_server -m read -f /wwwlogs/access.log
    
    write model example:
        python3 watcher.py -k access_log_80_server  -m write -p 4  [-with-static]
        
    """

    try:

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

    except TypeError as e:
        print('参数错误')
        print('参数说明 :')
        print('     -f  your access.log path')
        print('     -k  your redis key name')
        print('     -m  run model -m [read | write]')
        print('     -p  writer model Proccess Number defualt 2 ')
        print('     -with-static  writer model Proccess will not filter static file request ')
        print('read model example :')
        print('     python3 watcher.py -k access_log_80_server -m read -f /wwwlogs/access.log ')
        print('write model example :')
        print('     python3 watcher.py -k access_log_80_server  -m write -p 4  [-with-static]')


    except Exception as e:
        traceback.print_exc()




