import time,json,sys,os
sys.path.append(os.getcwd() + '/../DataBase')
from DataBase.Mongo import MongoDb
from flask import Flask ,render_template,request,jsonify,logging
import multiprocessing


app = Flask(__name__)



class analysisa:

    def __init__(self):
        totday  = time.strftime("%Y_%m_%d", time.localtime(time.time()))
        self.dbName = 'xfb'
        self.dbCollection = 'xfb_online_%s_log' % totday
        self.db = MongoDb(self.dbName,self.dbCollection).db


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
        _list = []
        for i in res:
            _list.append(i)

        return _list

    # 获取某个ip的访问详情
    def getTop10IpDetail(self ,ip ,page ,limit=10):
        # 获取某个ip的访问详情
        ip = ip.strip()
        offset = (page-1)*limit

        # 查询中 object_id 如果是对象 json.dumps会报错
        res = self.db.find({'ip': {'$eq': ip}},{'_id':0} ).sort('time_int', -1).skip(offset).limit(limit)
        count = self.db.find({'ip': {'$eq': ip}},{'_id':0} ).count()


        _list = list(res)

        return (_list,count)

    # 统计访问前十对应的ip 访问了哪些 页面 以及 每个页面 的对应的 次数
    def getTop10IpWitheveryPage(self):
        # 统计每个ip 访问的次数
        exp = [
            {'$project': {'ip':'$ip', '_id': 0, 'country': 1, 'city': 1 ,'user_agent':1}},
            # {'$group':{'_id':'$ip' ,'total_num':{'$sum':1} ,'country':{'$addToSet': '$country'} ,'city':{'$addToSet': '$city'} }},
            {'$group': {'_id': '$ip', 'total_num': {'$sum': 1}, 'country': {'$addToSet': '$country'},'ua':{'$addToSet':'$user_agent'},'city': {'$addToSet': '$city'}}},
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
        _list = []
        for i in res:
            _list.append(i)
        return _list

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
        _list = []
        for i in res:
            _list.append(i)
        return _list

    def getTopStatus(self):
        # 统计来访者的国家
        exp = [
            # {'$group': {'_id': '$status', 'total_num': {'$sum': 1} ,'pages':{'$push':"$url"} }},
            {'$group': {'_id': '$status', 'total_num': {'$sum': 1} }},
            {'$sort': {'total_num': -1}},
            # {'$limit': 10},
        ]
        res = self.db.aggregate(exp)
        _list = []
        for i in res:
            _list.append(i)
        return _list

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

        _list = []
        for i in res:
            _list.append(i)
        return _list

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
        # self.getAllIp()
        pass


@app.route('/')
def index():
    return render_template('index.html')
    pass

@app.route('/getApiMap')
def get_api_map():

    str = '打开监控控制面板 <br/>'
    str += '/ <br/>'
    str += '<hr/>'

    str =  '获取访问前十 的ip <br/>'
    str += '/getTop10Ip <br/>'
    str += '<hr/>'

    str += '获取访问前十 的ip 以及 访问每个页面的次数 以及 时间 <br/>'
    str += '/getTop10IpWitheveryPage <br/>'
    str += '<hr/>'

    str += '所有访问最多的请求页面<br/>'
    str += '/getTopRequsetMostPage <br/>'
    str += '<hr/>'

    str += '所有国家访问的次数<br/>'
    str += '/getTop10RequstCountry<br/>'
    str += '<hr/>'

    str += '所有请求次数的统计<br/>'
    str += '/getTopStatus<br/>'
    str += '<hr/>'

    str += '总的ip的请求数<br/>'
    str += '/getAllIp<br/>'

    return  str

@app.route('/getTop10Ip')
def getTop10Ip():
    res = analysisa().getTop10Ip()
    return json.dumps(res, ensure_ascii=False)


@app.route('/getTop10IpDetail',methods=['get','post'])
def getTop10IpDetail():
    if(request.method == 'GET'):
        return render_template('top_ip_detail.html')

    if(request.method == 'POST'):
        ip = request.form.get('ip')
        p = request.form.get('page')
        l = request.form.get('limit')
        res = analysisa().getTop10IpDetail(ip ,page = int(p),limit = int(l))

        _return = {
          "code": 0,
          "msg": "success",
          "count": res[1],
          "data": res[0]
        }
        return json.dumps(_return, ensure_ascii=False)




@app.route('/getTop10IpWitheveryPage')
def getTop10IpWitheveryPage():
    res = analysisa().getTop10IpWitheveryPage()
    return json.dumps(res, ensure_ascii=False)

@app.route('/getTopRequsetMostPage')
def getTopRequsetMostPage():
    res = analysisa().getTopRequsetMostPage()
    return json.dumps(res, ensure_ascii=False)

@app.route('/getTop10RequstCountry')
def getTop10RequstCountry():
    res = analysisa().getTop10RequstCountry()
    return json.dumps(res, ensure_ascii=False)

@app.route('/getAllStatus')
def getAllStatus():
    res = analysisa().getTopStatus()
    return json.dumps(res, ensure_ascii=False)

@app.route('/getAllIp')
def getAllIp():
    res = analysisa().getAllIp()
    return json.dumps(res, ensure_ascii=False)




if __name__ == "__main__":

    # analysisa().getTop10IpDetail()
    app.debug = False
    app.run(host='0.0.0.0')















