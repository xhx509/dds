#!/usr/bin/env python3
import datetime
import os
import platform
import socket
import subprocess as sp
import sys
import time
from dds_log_service import DDSLogs


STATE_DDS_NOTIFY_NET_VIA = 'net_via'
DDH_GUI_UDP_PORT = 12349
lg = DDSLogs('net')
_sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _u(s, ip='127.0.0.1', port=DDH_GUI_UDP_PORT):
    if '/' not in s:
        s += '/'
    _sk.sendto(s.encode(), (ip, port))


def _w_pid(s):
    if platform.system() != 'Linux':
        return
    path = '/tmp/{}.pid'.format(s)
    if os.path.exists(path):
        os.remove(path)
    pid = str(os.getpid())
    f = open(path, 'w')
    f.write(pid)
    f.close()


def _is_rpi():
    return os.uname().nodename in ('raspberrypi', 'rpi')


def _only_one_of_me(name):

    ooi = _only_one_of_me
    ooi._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        # '\0' so does not take a filesystem entry
        ooi._lock_socket.bind('\0' + name)

    except socket.error:
        s = '{} already running so NOT executing this one'
        print(s.format(name))
        sys.exit(1)


def _sh(s: str) -> bool:
    rv = sp.run(s, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode == 0


def _p(s):
    lg.a(s)
    print(s)


def main():

    if not _is_rpi():
        _p('laptop')
        _u('{}/laptop'.format(STATE_DDS_NOTIFY_NET_VIA))
        time.sleep(60)
        return

    # wi-fi can go internet and we already use it
    wlan_has_via = _sh('timeout 2 ping -c 1 -I wlan0 www.google.com')
    if wlan_has_via and _sh('ip route get 8.8.8.8 | grep wlan0'):
        _p('wifi')
        _u('{}/wifi'.format(STATE_DDS_NOTIFY_NET_VIA))
        time.sleep(60)
        return

    # wi-fi cannot go internet, are we really using it
    if not _sh('/usr/sbin/ifmetric ppp0 400'):
        _p('ifmetric error ppp0 400')
        time.sleep(2)

    # wi-fi, try again
    wlan_has_via = _sh('timeout 2 ping -c 1 -I wlan0 www.google.com')
    if wlan_has_via and _sh('ip route get 8.8.8.8 | grep wlan0'):
        _p('* wi-fi *')
        _u('{}/wifi'.format(STATE_DDS_NOTIFY_NET_VIA))
        time.sleep(60)
        return

    # wi-fi does NOT work, make sure we try cell
    if not _sh('/usr/sbin/ifmetric ppp0 0'):
        _p('ifmetric error ppp0 0')
        time.sleep(2)

    # check cell can go to internet
    ppp_has_via = _sh('timeout 2 ping -c 1 -I ppp0 www.google.com')
    if ppp_has_via and _sh('ip route get 8.8.8.8 | grep ppp0'):
        _p('cell')
        _u('{}/cell'.format(STATE_DDS_NOTIFY_NET_VIA))
        time.sleep(300)
        return

    _p('none')


if __name__ == '__main__':

    _only_one_of_me('dds-net')
    _w_pid('dds-net')

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('log created on {}'.format(now))

    while 1:
        main()
