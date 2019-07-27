from DataBase.NoSql import Model
from redis import Redis as RedisClient

class Redis(Model):
    db = False
    def __init__(self ,DbName = 0):
        if self.db == False:
            self.db = RedisClient(
                host=self.getConfig()['host'],
                port=self.getConfig()['port'],
                password=self.getConfig()['auth'],
                db= DbName,
                decode_responses=True,
                retry_on_timeout=10,
            )




if __name__ == "__main__":
    # example
    # Redis(10).db.set('key','value')
    pass


