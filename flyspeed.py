#!/usr/bin/env python

import os
import sys
import time
import threading 
import urllib2
import socket
import re

RE_PING_TIME = re.compile('time=([\d.]+?) ms')
 
class Download(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url
        self.thread_num = 1
        self.interval = 1
        self.thread_stop = False
        self.datasize=0
        self.start_time=0
        self.end_time=0
   
    def do_download(self, url):
        buffer_size = 1024
        try:
            uf = urllib2.urlopen(url, timeout=4)
            self.start_time=time.time()
            while True:
                data = uf.read(buffer_size)
                if not data or self.thread_stop: break
                self.datasize += buffer_size
        except Exception as e:
            pass
 
    def run(self):
        self.do_download(self.url)

    def terminate(self):  
        self.thread_stop = True

class Ping(threading.Thread):
    def __init__(self, ip):
        threading.Thread.__init__(self)
        self.ip = ip
        self.thread_num = 1
        self.thread_stop = False
        self.ping_result = 0

    def do_ping(self, ip):
        tmp = os.popen("ping -c 1 "+ip).read()
        try:
            self.ping_result = float(RE_PING_TIME.findall(tmp)[0])
        except:
            pass

    def run(self):
        self.do_ping(self.ip)

    def terminate(self):
        self.thread_stop = True
        


def benchmark(start=1, end=39, server_type="ssh"):
    ping_kv={}
    download_kv={}
    print ">>> Starting..."
    for i in range(start, end+1):
        i_str = str(i)
        if i < 10 and server_type == "ssh": i_str = '0' + i_str
        domain_prefix = server_type
        if server_type == "ssh": domain_prefix = "s"
        domain_suffix = ".flyssh.net"
        domain = domain_prefix + i_str + domain_suffix
        try:
            ip = socket.gethostbyname_ex(domain)[2][0]
            url = 'http://' + str(ip) + '/10mb.bin'
            print domain + ":",
            download = Download(url)
            download.daemon = True
            download.start()

            ping_results = []
            for intv in range(5):
                print str(5-intv) + '..', 
                sys.stdout.flush()
                try:
                    ping = Ping(ip)
                    ping.daemon = True
                    ping.start()
                    time.sleep(1)
                    ping.terminate()
                    #print ping.ping_result
                    if ping.ping_result != 0: ping_results.append(ping.ping_result)
                except Exception as e:
                    print e
                    pass

            if ping_results != []:
                ping_result_avg = int( sum(ping_results) / len(ping_results) )
                print "[ PING: %d ms ]" % ping_result_avg,
                ping_kv[domain] = ping_result_avg
            else:
                print "[ PING: Error ]",
                ping_kv[domain] = 99999

            download.end_time=time.time()
            download.terminate()
            delta = download.end_time - download.start_time
            speed = int(download.datasize / delta / 1024)

            if speed != 0:
                print "[ DOWNLOAD: %d KB/s ]" % speed
                download_kv[domain] = speed
            else:
                print "[ DOWNLOAD: Error ]" 
                download_kv[domain] = 0
        except KeyboardInterrupt:
            download.terminate()
            sys.exit(0)
        except Exception as e:
            continue
    print ">>> Done!"
    return ping_kv, download_kv

def show_help():
    print "Usage:"
    print "$ python flyspeed.py [ssh|vpn] [start_server_no-end_server_no] [top_number]"
    print
    print "Examples:"
    print "$ python flyspeed.py"
    print "$ python flyspeed.py ssh"
    print "$ python flyspeed.py ssh 12"
    print "$ python flyspeed.py ssh 1-10"
    print "$ python flyspeed.py ssh 2-15 5"
    print "$ python flyspeed.py vpn 1-10 3"
    print
    print "Defaults: "
    print "$ python flyspeed.py ssh 1-39 5"
    print
    print "Feel free to submit a ticket in our client center when you need further help :)"
    sys.exit(0)

if __name__ == '__main__':
    server_type, start, end, top_number = "ssh", 1, 39, 5 # defaults

    if len(sys.argv) > 1: # == 2, 3, 4
        server_type = sys.argv[1]
        if server_type not in ["ssh", "vpn"]:
            show_help()

    if len(sys.argv) > 2: # == 3, 4
        start_end = sys.argv[2].strip('-')
        if start_end.count('-') == 1 and start_end.replace('-','').isdigit():
            start, end = start_end.split('-')
        elif start_end.isdigit():
            start = end = start_end
        else:
            show_help()
        start, end = int(start), int(end)
        if start < 1: start =1
        if server_type == "ssh" and end > 40: end = 40
        if server_type == "vpn" and end > 20: end = 20

    if len(sys.argv) > 3: # == 4
        top_number = sys.argv[3]
        if not top_number.isdigit(): show_help()
        top_number = int(top_number)
        if top_number > end - start + 1: top_number = end - start + 1
        if top_number < 1: top_number = 1

    if len(sys.argv) > 4: show_help()

    ping_kv, download_kv = benchmark(start, end, server_type)
    if top_number > len(ping_kv): top_number = len(ping_kv)
    if top_number == 1: sys.exit(0)
    if top_number == 0:
        print ">>> No servers available!"
        sys.exit(2)

    print ">>> Top %d Servers:" % top_number
    print "PING:"
    ping_list = sorted(ping_kv.items(), key=lambda item:item[1], reverse=False)
    for i in ping_list[:top_number]:
        if i[1] > 99998: 
            print i[0], "(failed)"
        else:
            print i[0], "(%s ms)" % i[1]
    print "DOWNLOAD:"
    download_list = sorted(download_kv.items(), key=lambda item:item[1], reverse=True)
    for i in download_list[:top_number]:
        print i[0], "(%s KB/s)" % i[1]

