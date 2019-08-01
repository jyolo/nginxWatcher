import os,subprocess


if __name__ == '__main__':

    aa = os.system('nohup python3 -u watcher.py -f  /mnt/hgfs/MyPythonProject/nginxWatcher/log/xfb.log > read.log  2>&1 &')
    print(aa)
    # subprocess.call('python3 -h')
