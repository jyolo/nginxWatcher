### Nginx 流量监控


#### 分布式nginx日志监控
    可分布式部署到多台服务器上,同时监控多台服务器的nginx流量 
    
#### 快速开始
    
    配置好　Database 里面的 config.json　相关数据库　默认　redis + monogodb　(暂不支持mysql可自行完善)
    
    配置好后就可以直接使用　参数说明  : 
        -f  access.log path
        -k  redis list key name  
        -m  run model -m [read | write]  
        -p  writer model Proccess Number 
        -with-static  输出到mongodb的时候是否保留过滤静态文件的请求日志; 默认过滤
    
    读取日志示例:
        python3 watcher.py -k access_log_80_server -m read -f /wwwlogs/access.log
    
    输出日志到mongodb:
        python3 watcher.py -k access_log_80_server  -m write -p 4  [-with-static]



## 启动脚本 
    
    1：安装依赖包 pip install -r requirements.txt
    
    python3 watcher.py -k access_log_80_server -m read -f /wwwlogs/access.log
    
    后台挂起　-u 关闭　python 缓冲
    nohup　python3 -u watcher.py -k access_log_80_server -m read -f /wwwlogs/access.log　> ./log/read.out  2>&1 &
         
    note: watch 对应的日志文件.log  [ 支持多个nginx日志 同时监控 ]
    
    2:快速读写一起　启动
    python3 start.py -k tt -p 5 -f /www/wwwlogs/your.log

## 停止脚本

    python3 stopWatcher.py
