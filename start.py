import sys,os


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

if __name__ == "__main__":
    args = formCommands(sys.argv)

    read_cmd = 'nohup python3 -u watcher.py -k %s -f %s > ./log/%s_read.out 2>&1 &'
    write_cmd = 'nohup python3 -u watcher.py -k %s -p 2 -m write > ./log/%s_write.out 2>&1 &'
    # read_cmd = 'python3 -u watcher.py -k %s -f %s > ./log/%s_read.out 2>&1 '

    file = key = ''

    if(args['logPath'] != None):
        file = args['logPath']

    if (args['redisKey'] != None):
        key = args['redisKey']

    read_cmd = read_cmd % (key,file, key)
    write_cmd = write_cmd % (key ,key)

    # print(read_cmd)
    # print(write_cmd)
    os.popen(read_cmd)
    os.popen(write_cmd)
    print('读写服务器已启动')
