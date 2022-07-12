import time
from dds.logs import l_e_, l_i_
from mat.ddh_shared import *


class AppBLEException(Exception):
    pass


def ble_die(e):
    l_e_('[ BLE ] error interact -> {}'.format(e))
    raise AppBLEException(e)


def ble_ok(s):
    l_i_('[ BLE ] interact -> {}'.format(s))


def check_local_file_exists(file_name, size, fol):
    path = os.path.join(fol, file_name)
    if os.path.isfile(path):
        return os.path.getsize(path) == size
    return False


def utils_ble_build_files_to_download_as_dict(lc, ls) -> dict:
    ff, fol = {}, get_dl_folder_path_from_mac(lc.address)
    for name, size in ls.items():
        if name.endswith('cfg'):
            continue
        if size and not check_local_file_exists(name, size, fol):
            ff[name] = size
    ble_ok('{} has {} files for us'.format(lc.address, len(ff)))
    return ff


def utils_ble_set_last_haul(fol, s):
    # careful 's' may be full path or only last part
    s = os.path.basename(os.path.normpath(s))
    path = str(fol) + '/.last_haul.json'
    d = {
        'file': s
    }
    with open(path, 'w') as f:
        json.dump(d, f)


def ble_li_ls_all(lc, dbg_pre_rm=False) -> dict:
    mac = lc.address
    if dbg_pre_rm:
        fol = str(get_dds_folder_path_dl_files())
        fol += '/{}/'.format(mac.replace(':', '-').lower())
        # todo: test this path before doing anyrmtree()
        print(fol)
        # shutil.rmtree(fol, ignore_errors=True)

    create_folder_logger_by_mac(mac)
    rv = lc.ble_cmd_dir()
    if rv == b'ERR':
        ble_die(__name__)
    ble_ok('list files: {}'.format(rv))
    return rv


def ble_li_rm_already_have(lc, ls):

    fol = get_dl_folder_path_from_mac(lc.address)
    for name, size in ls.items():
        if name.endswith('cfg'):
            continue
        if name.startswith('dummy'):
            continue
        if check_local_file_exists(name, size, fol):
            rv = lc.ble_cmd_del(name)
            if not rv:
                ble_die('failed del already had file {}'.format(name))
            ble_ok('OK removing file {} from logger'.format(name))
            time.sleep(3)


def ble_li_rws(lc, g):  # does not exist on RN4020
    lat, lon, _ = g
    lat = '{:+.6f}'.format(float(lat))
    lon = '{:+.6f}'.format(float(lon))
    s = '{} {}'.format(lat, lon)
    rv = lc.ble_cmd_rws(s)
    if not rv:
        ble_die('error ble_li_rws')
    ble_ok('RWS OK: lat {} lon {}'.format(lat, lon))


def ble_li_run(lc):
    if not lc.ble_cmd_run():
        ble_die('RUN failed')
    ble_ok('RUN')


def ble_li_bat(lc):
    rv = lc.ble_cmd_bat()
    if rv:
        ble_ok('BAT {} mv'.format(rv))
        return
    ble_die('retrieving bat failed')


def ble_li_gfv(lc):
    rv = lc.ble_cmd_gfv()
    ble_ok('GFV {}'.format(rv))


def ble_li_bsy(lc):
    rv = None
    for i in range(3):
        rv = lc.ble_cmd_bsy()
        if rv == 'not_busy':
            ble_ok('logger not busy')
            return
        time.sleep(3)

    if rv is None:
        l_e_('BSY command got no answer')
    if rv == 'busy':
        ble_die('logger answered as busy')


def ble_li_con(lc):
    for i in range(3):
        rv = lc.ble_cmd_con()
        ble_ok('connection parameter set to {}'.format(rv))
        if rv == 'CO2':
            return
        time.sleep(1)

    ble_die('connection parameter for RPI failed!')


def ble_li_del(lc, s):
    rv = lc.ble_cmd_del(s)
    if not rv:
        ble_die('del {} failed'.format(s))


def ble_li_mts(lc):
    rv = lc.ble_cmd_mts()
    if not rv:
        ble_die('mts failed')


def ble_li_btc(lc):
    if not lc.ble_cmd_btc():
        ble_die('setting BTC')
    ble_ok('BTC OK')


def ble_li_gdo(lc):
    for i in range(3):
        dos, dop, dot = lc.ble_cmd_gdo()
        if dos == '' or (dos == '0000' and dop == '0000' and dot == '0000'):
            l_e_('GDO bad -> {}'.format((dos, dop, dot)))
            time.sleep(2)
            continue

        ble_ok('GDO: {}'.format((dos, dop, dot)))
        return True


def ble_li_ping(lc):
    # will do something only for RN4020 loggers
    rv = lc.ble_cmd_ping()
    if rv:
        ble_ok('ping')
        return
    if type(rv) is bytes:
        rv = rv.decode()
    ble_die('ping {}'.format(rv))


def ble_li_sws(lc, g):  # STOP with STRING

    rv = lc.ble_cmd_sts()
    if rv == 'stopped':
        ble_ok('SWS not required')
        return

    # send SWS command: parameter has NO comma
    lat, lon, _ = g
    lat = '{:+.6f}'.format(float(lat))
    lon = '{:+.6f}'.format(float(lon))
    s = '{} {}'.format(lat, lon)
    rv = lc.ble_cmd_sws(s)
    if not rv:
        ble_die('SWS')
    ble_ok('SWS coordinates {}'.format(s))


def ble_li_time_sync(lc):
    dt = lc.ble_cmd_gtm()
    if dt is None:
        ble_die('error gtm at time sync')
    ble_ok('time is {}'.format(dt))

    rv = lc.ble_cmd_stm()
    if not rv:
        ble_die('error stm at time sync')
    ble_ok('time sync OK')
