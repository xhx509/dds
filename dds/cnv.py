import time
from dds.logs import lg_cnv as lg
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import *
from settings import ctx


_g_ts_cnv = 0
PERIOD_CNV_SECS = 600


def _cnv(m):
    fol = str(get_dds_folder_path_dl_files())
    s = 'converting {} on fol {}'
    lg.a(s.format(m, fol))
    rv, _ = ddh_convert_lid_to_csv(fol, m)
    return rv


def cnv_serve():

    global _g_ts_cnv
    now = time.perf_counter()
    if now < _g_ts_cnv:
        return

    if _g_ts_cnv == 0:
        lg.a('doing first conversion ever')

    _g_ts_cnv = now + PERIOD_CNV_SECS
    e = ''

    rv = _cnv('_DissolvedOxygen')
    if not rv:
        e += 'O'
    rv = _cnv('_Temperature')
    if not rv:
        e += 'T'
    rv = _cnv('_Pressure')
    if not rv:
        e += 'P'
    if e:
        _u('{}/{}'.format(STATE_DDS_NOTIFY_CONVERSION_ERR, e))
    else:
        _u('{}/OK'.format(STATE_DDS_NOTIFY_CONVERSION_OK))
    lg.a('finished conversion round')
