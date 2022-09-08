import time

from dds.logs import lg_cnv as lg
from mat.ddh_shared import get_dds_folder_path_dl_files, ddh_convert_lid_to_csv
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import STATE_DDS_NOTIFY_CONVERSION_RESULT as _R
from settings import ctx


def _cnv(m):
    fol = str(get_dds_folder_path_dl_files())
    s = 'converting {} on fol {}'
    lg.a(s.format(m, fol))
    rv, _ = ddh_convert_lid_to_csv(fol, m)
    return rv


def cnv_serve():
    now = time.perf_counter()
    if ctx.ts_last_cnv == 0:
        lg.a('doing first conversion ever')
    else:
        # todo > set this time as constant somewhere
        if ctx.ts_last_cnv + 30 > now:
            return
        lg.a('lets see if we have stuff to convert')

    ctx.ts_last_cnv = now
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
        _u('{}/{}'.format(_R, e))
    else:
        _u('{}/OK'.format(_R))
    lg.a('finished conversion round')
