import os,json


class Model:

    __instance = False
    _DbSetting = {}



    # 单列
    def __new__(cls, *args, **kwargs):
        cls.configFilePath = os.path.dirname(__file__) + '/config.json'
        # 配置文件不存在
        if os.path.exists(cls.configFilePath) == False:
            raise FileNotFoundError('config.json is not exists')
        if cls.__instance == False:
            cls.__instance = object.__new__(cls)

        return cls.__instance


    def getConfig(self ):
        DriverName = self.__instance.__class__.__name__
        fileIo = open(self.configFilePath, 'r', 1, 'UTF-8')
        setting = json.load(fileIo)[DriverName]
        fileIo.close()

        return setting



if __name__ == "__main__":
    # db = Model()
    # print(db)
    pass