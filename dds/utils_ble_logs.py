import datetime
import queue
import threading
import time
from pathlib import Path
from mat.ddh_shared import dds_get_json_vessel_name, get_dds_folder_path_dl_files
from mat.utils import PrintColors as PC


qt = queue.Queue()
ql = queue.Queue()


def _logs_core_get_folder():
    return 'logs'


def _log_init(d):

    # create folder if it does not exist
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    path = '{}/{}'.format(d, 'dds_{}.log'.format(ts))

    def _th_fxn():
        while 1:
            # use logging queue
            s = ql.get()
            with open(path, 'a') as f:
                f.write(s)

    th = threading.Thread(target=_th_fxn)
    th.start()


def _tracker_init(d, vessel_name):

    # create folder if it does not exist
    d = '{}/ddh_{}/'.format(d, vessel_name)
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    path = '{}/track_{}_{}.txt'.format(d, vessel_name, ts)

    def _th_fxn():
        while 1:
            # use tracking queue
            s = qt.get()
            with open(path, 'a') as f:
                f.write(s)

    th = threading.Thread(target=_th_fxn)
    th.start()


def _l_l_(s, cb):
    now = datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S')
    s = '{} | {}'.format(now, s)
    # 'cb' is a colored print to console
    cb(s)
    ql.put(s + '\n')


def l_w_(s): _l_l_(s, PC.Y)
def l_i_(s): _l_l_(s, PC.N)
def l_d_(s): _l_l_(s, PC.B)
def l_e_(s): _l_l_(s, PC.R)


g_last_time_track_log = time.perf_counter()


def log_tracking_update(lat, lon):
    global g_last_time_track_log
    now = time.perf_counter()
    if g_last_time_track_log + 10 < now:
        # too recent, leave
        return

    if lat:
        # (lat, lon, time)
        now = datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S')
        s = '{} | {}\n'.format(now, '{},{}'.format(lat, lon))
        qt.put(s)
        g_last_time_track_log = time.perf_counter()


def log_core_start_at_boot():
    d = str(_logs_core_get_folder())
    _log_init(d)
    time.sleep(.1)
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    l_w_('[ BLE ] log created on {}'.format(now))


def log_tracking_start_at_boot():
    v = dds_get_json_vessel_name().replace(' ', '_')
    d = str(get_dds_folder_path_dl_files())
    time.sleep(.1)
    _tracker_init(d, v)
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    l_w_('[ BLE ] track log created on {}'.format(now))

