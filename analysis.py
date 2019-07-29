import time
from DataBase.Mongo import MongoDb


class analysisa:

    def __init__(self):
        totday = time.strftime("%d", time.localtime(time.time()))

        self.dbName = 'xfb'
        self.dbCollection = 'xfb_online_%s_log' % totday

        self.db = MongoDb(self.dbName,self.dbCollection).db
        self.start()

    # 获取访问前十 的ip
    def getTop10Ip(self):
        # 统计每个ip 访问的次数
        exp = [
            {'$project': {'_id': 1, 'ip': 1, 'country': 1, 'city': 1}},
            # {'$group':{'_id':'$ip' ,'total_num':{'$sum':1} ,'country':{'$addToSet': '$country'} ,'city':{'$addToSet': '$city'} }},
            {'$group': {'_id': '$ip', 'total_num': {'$sum': 1}, 'country': {'$addToSet': '$country'},
                        'city': {'$addToSet': '$city'}}},
            {'$sort': {'total_num': -1}},
            {'$limit': 10},
        ]

        res = self.db.aggregate(exp)
        for i in res:
            print(i)

    # 统计访问前十对应的ip 访问了哪些 页面 以及 每个页面 的对应的 次数
    def getTop10IpWitheveryPage(self):
        # 统计每个ip 访问的次数
        exp = [
            {'$project': {'_id': 1, 'ip': 1, 'country': 1, 'city': 1}},
            # {'$group':{'_id':'$ip' ,'total_num':{'$sum':1} ,'country':{'$addToSet': '$country'} ,'city':{'$addToSet': '$city'} }},
            {'$group': {'_id': '$ip', 'total_num': {'$sum': 1}, 'country': {'$addToSet': '$country'},
                        'city': {'$addToSet': '$city'}}},
            {'$sort': {'total_num': -1}},
            {'$limit': 10},
        ]

        res = self.db.aggregate(exp)
        for i in res:
            print(i)

            exp = [
                {'$match':{'ip': {'$eq' : i['_id'] }} },
                {'$group': {'_id': '$url', 'total_num': {'$sum': 1} ,'times':{'$push':'$time_str'} }},
                {'$sort': {'total_num': -1}},
                {'$limit': 10},
            ]

            sub_res = self.db.aggregate(exp)

            for j in sub_res:
                print(j)

    # 统计被访问url的最多次数的页面
    def getTopRequsetMostPage(self):
        exp = [
            {'$group': {'_id': '$url', 'total_num': {'$sum': 1}}},
            {'$sort': {'total_num': -1}},
            {'$limit': 20},
        ]
        res = self.db.aggregate(exp)
        for i in res:
            print(i)

    def getTop10RequstCountry(self):
        # 统计来访者的国家
        exp = [
            {'$group': {'_id': '$country', 'total_num': {'$sum': 1} ,'ip':{'$push':'$ip'} }},
            {'$sort': {'total_num': -1}},
            {'$limit': 20},
        ]
        res = self.db.aggregate(exp)
        for i in res:
            print(i)


    def start(self):
        # 获取访问前十 的ip
        self.getTop10Ip()

        # self.getTop10IpWitheveryPage()

        # self.getTopRequsetMostPage()









if __name__ == "__main__":

    analysisa()