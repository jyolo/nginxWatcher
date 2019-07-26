from DataBase.Mongo import MongoDb


class analysisa:

    def __init__(self):
        self.db = MongoDb('xfb','xfb_log').db
        self.start()

    def start(self):
        # 统计每个ip 访问的次数
        exp = [
            { '$project': {'_id': 1, 'ip': 1, 'country': 1, 'city': 1}},
            {'$group':{'_id':'$ip' ,'total_num':{'$sum':1} ,'country':{'$addToSet': '$country'} ,'city':{'$addToSet': '$city'} }},
            {'$sort': {'total_num': -1}},
            {'$limit': 20},
        ]

        res = self.db.aggregate(exp)
        for i in res:
            # print(i['_id'] ,i['total_num'])

            # 统计每个对应的ip 访问了哪些 页面 以及 每个页面 的对应的 次数
            exp = [
                {'$match':{'ip': {'$eq' : i['_id'] }} },
                {'$group': {'_id': '$url', 'total_num': {'$sum': 1} ,'times':{'$push':'$time_str'} }},
                {'$sort': {'total_num': -1}},
                {'$limit': 10},
            ]

            sub_res = self.db.aggregate(exp)
            print(i['_id'] ,i['country'][0])
            # print()
            for j in sub_res:

                print(j)



        # 统计被访问url的最多次数的站点
        # exp = [
        #     {'$group': {'_id': '$url', 'total_num': {'$sum': 1}}},
        #     {'$sort': {'total_num': -1}},
        #     {'$limit': 20},
        # ]
        # res = self.db.aggregate(exp)
        # for i in res:
        #     print(i)

        # # 统计来访者的国家
        # exp = [
        #     {'$group': {'_id': '$country', 'total_num': {'$sum': 1}}},
        #     {'$sort': {'total_num': -1}},
        #     {'$limit': 20},
        # ]
        # res = self.db.aggregate(exp)
        # for i in res:
        #     print(i)



if __name__ == "__main__":

    analysisa()