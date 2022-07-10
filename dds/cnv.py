import glob
import os
import threading
import time
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv
from mat.utils import linux_ls_by_ext


def _csv_pre_rm(fol, pre_rm=False):
    """ util to remove CSV files """

    if not pre_rm:
        return
    ff = linux_ls_by_ext(fol, 'csv')
    for _ in ff:
        os.remove(_)
        print('removed {}'.format(os.path.basename(_)))


def cnv_thread_start_at_boot(p_rm=False):

    fol = str(get_dds_folder_path_dl_files())

    def _cnv(m):
        ddh_convert_lid_to_csv(fol, m)

    def _fxn():
        _csv_pre_rm(fol, p_rm)
        _th_o = threading.Thread(target=_cnv, args=('_DissolvedOxygen', ))
        _th_t = threading.Thread(target=_cnv, args=('_Temperature', ))
        _th_p = threading.Thread(target=_cnv, args=('_Pressure', ))
        _th_o.start()
        _th_t.start()
        _th_p.start()

    while 1:
        _fxn()
        time.sleep(3600)
