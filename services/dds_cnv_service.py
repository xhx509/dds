import threading
import time
from dds.logs import l_i_
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv


def _cnv(m):
    fol = str(get_dds_folder_path_dl_files())
    s = '[ CNV ] started thread {} on fol {}'
    l_i_(s.format(m, fol))
    ddh_convert_lid_to_csv(fol, m)


def _fxn():
    _th_o = threading.Thread(target=_cnv, args=('_DissolvedOxygen', ))
    _th_t = threading.Thread(target=_cnv, args=('_Temperature', ))
    _th_p = threading.Thread(target=_cnv, args=('_Pressure', ))
    _th_o.start()
    _th_t.start()
    _th_p.start()


if __name__ == '__main__':
    while 1:
        _fxn()
        time.sleep(3600)
