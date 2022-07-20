#!/usr/bin/env python3
import datetime
import time
import subprocess as sp
from mat.dds_states import STATE_DDS_NOTIFY_NET_VIA
from mat.utils import linux_app_write_pid, linux_is_rpi, ensure_we_run_only_one_instance
from mat.ddh_shared import send_ddh_udp_gui as _u
from dds_log_service import DDSLogs


lg = DDSLogs('net')

# --------------------------------------
# todo: remove all imports to MAT so we can call this service without virtual environemtn in rpi
# -----------------------------------

def _sh(s: str) -> bool:
    rv = sp.run(s, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode == 0


def _p(s):
    lg.a(s)
    print(s)


def main():

    if not linux_is_rpi():
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

    ensure_we_run_only_one_instance('dds-net')
    linux_app_write_pid('dds-net')

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('log created on {}'.format(now))

    while 1:
        main()
