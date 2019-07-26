import os,json

def p(var):
    print(var)

def getDataBaseConfig(DriverName):
    # DriverName = self.__instance.__class__.__name__
    _path = os.path.dirname(__file__) + '/config.json'
    fileIo = open(_path, 'r', 1, 'UTF-8')
    setting = json.load(fileIo)[DriverName]
    fileIo.close()

    return setting