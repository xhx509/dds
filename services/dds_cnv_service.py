import datetime
import os
import threading
import time
from mat.dds_states import STATE_DDS_NOTIFY_CONVERSION
from services.dds_logs import DDSLogs
from dds.utils_ble_logs import l_e_
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv, get_dds_is_ble_downloading_flag, \
    PID_FILE_DDS_CNV
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance
from multiprocessing import Process
from settings import ctx
from mat.ddh_shared import send_ddh_udp_gui as _u


lg = DDSLogs('cnv')


def _p(s):
    lg.a(s)
    print(s)


def _cnv(m):
    fol = str(get_dds_folder_path_dl_files())
    s = '[ CNV ] started thread {} on fol {}'
    _p(s.format(m, fol))
    ddh_convert_lid_to_csv(fol, m)


def _fxn():
    _p('[ CNV ] session')
    _th_o = threading.Thread(target=_cnv, args=('_DissolvedOxygen', ))
    _th_t = threading.Thread(target=_cnv, args=('_Temperature', ))
    _th_p = threading.Thread(target=_cnv, args=('_Pressure', ))
    _th_o.start()
    _th_t.start()
    _th_p.start()


def _start_dds_cnv_service():

    ensure_we_run_only_one_instance('dds_cnv')
    linux_app_write_pid(PID_FILE_DDS_CNV)

    flag_dl = get_dds_is_ble_downloading_flag()

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('[ CNV ] log created on {}'.format(now))

    i = 0
    while 1:
        while os.path.isfile(flag_dl):
            _p('[ CNV ] not converting while BLE downloading')

        # every hour
        if i % 360 == 0:
            _fxn()

        _u('{}/pong'.format(STATE_DDS_NOTIFY_CONVERSION))
        time.sleep(10)
        i += 1


def start_dds_cnv_service():
    p = Process(target=_start_dds_cnv_service)
    p.start()
    ctx.proc_cnv = p


def is_dds_cnv_service_alive():
    if not ctx.proc_cnv.is_alive():
        l_e_('[ CNV ] DDS CNV service not alive')


if __name__ == '__main__':
    start_dds_cnv_service()
