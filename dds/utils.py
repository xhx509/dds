import os
import socket
import time
from dds.logs import lg_dds as lg
from mat.crc import calculate_local_file_crc
from mat.ddh_shared import dds_get_json_vessel_name, get_dds_folder_path_dl_files, get_dds_folder_path_logs, \
    DDH_GUI_UDP_PORT
from pathlib import Path
import datetime

from mat.dds_states import STATE_DDS_BLE_DOWNLOAD_PROGRESS

g_tracking_path = ''
g_last_time_track_log = time.perf_counter()
g_ts_scan_banner = 0


# these NORMAL logs are local
def dds_log_core_start_at_boot():

    # create NORMAL log folder if it does not exist
    d = str(get_dds_folder_path_logs())
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    lg.a('started normal logs on {}'.format(ts))


# these TRACKING logs get uploaded
def dds_log_tracking_start_at_boot():

    v = dds_get_json_vessel_name().replace(' ', '_')
    d = str(get_dds_folder_path_dl_files())

    # create TRACKING log folder if it does not exist
    d = '{}/ddh_{}/'.format(d, v)
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    lg.a('started tracking logs on {}'.format(ts))
    global g_tracking_path
    g_tracking_path = '{}/track_{}_{}.txt'.format(d, v, ts)


def dds_log_tracking_add(lat, lon):

    assert g_tracking_path != ''

    global g_last_time_track_log
    now = time.perf_counter()
    if g_last_time_track_log + 10 < now:
        # too recent, leave
        return

    if lat:
        now = datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S')
        s = '{} | {}\n'.format(now, '{},{}'.format(lat, lon))
        with open(g_tracking_path, 'a') as f:
            f.write(s)
        g_last_time_track_log = time.perf_counter()


def print_ble_scan_banner():
    global g_ts_scan_banner
    now = time.perf_counter()
    _first_banner = g_ts_scan_banner == 0
    _expired_banner = now > g_ts_scan_banner + 300
    if _first_banner or _expired_banner:
        g_ts_scan_banner = now + 300
        lg.a('scanning ...')


def crc_local_vs_remote(path, remote_crc):
    """ calculates local file name CRC and compares to parameter """

    # remote_crc: logger, crc: local
    crc = calculate_local_file_crc(path)
    crc = crc.lower()
    return crc == remote_crc, crc


def ble_progress_dl(data_len, size, ip='127.0.0.1', port=DDH_GUI_UDP_PORT):
    _ = int(data_len) / int(size) * 100 if size else 0
    _ = _ if _ < 100 else 100
    _sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('{} %'.format(int(_)))
    _ = '{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_PROGRESS, _)

    # always send to localhost
    _sk.sendto(str(_).encode(), (ip, port))

    if ip == '127.0.0.1':
        return

    # only maybe somewhere else :)
    # _sk.sendto(str(_).encode(), (ip, port))


def build_cmd(*args):

    # phone commands use aggregated, a.k.a. transparent, mode
    # they do NOT follow LI proprietary format (DWG NNABCD...)
    tp_mode = len(str(args[0]).split(' ')) > 1
    cmd = str(args[0])
    if tp_mode:
        to_send = cmd
    else:
        # build LI proprietary command format
        cmd = str(args[0])
        arg = str(args[1]) if len(args) == 2 else ''
        n = '{:02x}'.format(len(arg)) if arg else ''
        to_send = cmd + ' ' + n + arg
    to_send += chr(13)

    # debug
    # print(to_send.encode())

    # know command tag, ex: 'STP'
    tag = cmd[:3]
    return to_send, tag
