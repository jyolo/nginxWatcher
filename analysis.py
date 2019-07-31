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
            {'$project': {'_id': 1, 'ip': 1, 'country': 1,'province':1, 'city': 1}},
            # {'$group':{'_id':'$ip' ,'total_num':{'$sum':1} ,'country':{'$addToSet': '$country'} ,'city':{'$addToSet': '$city'} }},
            {'$group': {'_id': '$ip', 'total_num': {'$sum': 1}, 'country': {'$addToSet': '$country'},'province':{'$addToSet':'$province'},
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
        _list = []
        for i in res:
            # print(i)

            exp = [
                {'$match':{'ip': {'$eq' : i['_id'] }} },
                {'$group': {'_id': '$url', 'total_num': {'$sum': 1} ,'times':{'$push':'$time_str'} }},
                {'$sort': {'total_num': -1}},
                {'$limit': 10},
            ]
            sub_res = self.db.aggregate(exp)
            i['pages'] = []
            i['page_request_nums'] = []
            i['page_request_times'] = []
            for j in sub_res:
                i['pages'].append(j['_id'])
                i['page_request_nums'].append(j['total_num'])
                i['page_request_times'].append(j['times'])


            _list.append(i)


        return _list



    # 统计被访问url的最多次数的页面
    def getTopRequsetMostPage(self):
        exp = [
            {'$group': {'_id': '$url', 'total_num': {'$sum': 1}}},
            {'$sort': {'total_num': -1}},
            {'$limit': 50},
        ]
        res = self.db.aggregate(exp)
        for i in res:
            print(i)

    # 所有国家访问的次数
    def getTop10RequstCountry(self):
        # 统计来访者的国家
        exp = [
            # {'$group': {'_id': '$country', 'total_num': {'$sum': 1} ,'ip':{'$push':'$ip'} }},
            {'$group': {'_id': '$country', 'total_num': {'$sum': 1}  }},
            {'$sort': {'total_num': -1}},
            # {'$limit': 20},
        ]
        res = self.db.aggregate(exp)
        for i in res:
            print(i)

    def getTopStatus(self):
        # 统计来访者的国家
        exp = [
            # {'$group': {'_id': '$status', 'total_num': {'$sum': 1} ,'pages':{'$push':"$url"} }},
            {'$group': {'_id': '$status', 'total_num': {'$sum': 1} }},
            {'$sort': {'total_num': -1}},
            # {'$limit': 10},
        ]
        res = self.db.aggregate(exp)
        for i in res:
            print(i)

    # 总的ip的请求数
    def getAllIp(self):
        # 第二个group  对第一个 group的值 进行 count
        exp = [
            # {'$group': {'_id': '$status', 'total_num': {'$sum': 1} ,'pages':{'$push':"$url"} }},
            {'$group': {'_id': '$ip'}},
            {'$group': {'_id': 1 ,'count':{'$sum':1 }}},
            # {'$limit': 10},
        ]
        res = self.db.aggregate(exp)

        for i in res:
            print(i)

    def start(self):
        # 获取访问前十 的ip
        # self.getTop10Ip()
        # 获取访问前十 的ip 以及 访问每个页面的次数 以及 时间
        # self.getTop10IpWitheveryPage()
        # 所有访问最多的请求页面
        # self.getTopRequsetMostPage()
        # 所有国家访问的次数
        # self.getTop10RequstCountry()
        # 所有请求次数的统计
        # self.getTopStatus()
        # 总的ip的请求数
        self.getAllIp()







if __name__ == "__main__":

    analysisa()