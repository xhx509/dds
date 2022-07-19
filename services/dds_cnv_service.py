import datetime
import os
import threading
import time
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv, get_dds_is_ble_downloading_flag
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance
from dds_log_service import DDSLogs


lg = DDSLogs('cnv')


def _p(s):
    lg.a(s)
    print(s)


def _cnv(m):
    fol = str(get_dds_folder_path_dl_files())
    s = 'started thread {} on fol {}'
    _p(s.format(m, fol))
    ddh_convert_lid_to_csv(fol, m)


def _fxn():
    _th_o = threading.Thread(target=_cnv, args=('_DissolvedOxygen', ))
    _th_t = threading.Thread(target=_cnv, args=('_Temperature', ))
    _th_p = threading.Thread(target=_cnv, args=('_Pressure', ))
    _th_o.start()
    _th_t.start()
    _th_p.start()


if __name__ == '__main__':

    ensure_we_run_only_one_instance('dds-cnv')
    linux_app_write_pid('dds-cnv')

    flag = get_dds_is_ble_downloading_flag()

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('log created on {}'.format(now))

    while 1:
        break_t = 0
        while os.path.isfile(flag) and break_t < 5:
            _p('not converting while BLE downloading')
            time.sleep(60)
            break_t += 1
        _fxn()
        time.sleep(3600)
