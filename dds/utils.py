import time

from dds.logs import lg_dds as lg
from mat.ddh_shared import dds_get_json_vessel_name, get_dds_folder_path_dl_files, get_dds_folder_path_logs
from pathlib import Path
import datetime


g_tracking_path = ''


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


g_last_time_track_log = time.perf_counter()


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

