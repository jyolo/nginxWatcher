from pymongo import MongoClient,client_session
from DataBase.NoSql import Model
from bson import ObjectId
from urllib.parse import quote_plus


class MongoDb(Model):

    db = False

    def __init__(self ,tableName,collectionName):

        # if(self.db == False):

        if len(self.getConfig()['username']) == 0   and len(self.getConfig()['password']) == 0:
            self.Connecter = MongoClient(host=self.getConfig()['host'] ,port= int(self.getConfig()['port']))
        else:
            url = "mongodb://%s:%s@%s:%s/%s" % (
                quote_plus(self.getConfig()['username']),
                quote_plus(self.getConfig()['password']),
                quote_plus(self.getConfig()['host']),
                self.getConfig()['port'],
                quote_plus(self.getConfig()['database'])
            )
            self.Connecter = MongoClient(url)


        self.db = self.Connecter[tableName][collectionName]






    def getObjectId(self):
        return ObjectId()


if __name__ == "__main__":
    # example
    # mongo = MongoDb('xfb','complaint')
    # print(mongo)
    # mongo.db.insert_one({'asd':'asd'})

    pass
