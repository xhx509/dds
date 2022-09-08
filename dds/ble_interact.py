import os
import pathlib
import shutil
import traceback
import bluepy.btle as ble
import time

from pandas.io import json

from dds.macs import macs_black, macs_orange, rm_mac_black, rm_mac_orange, add_mac_orange, add_mac_black, \
    is_mac_in_black, is_mac_in_orange
from dds.sns import sns_notify_logger_error, sns_notify_ble_scan_exception
from mat.ble.bluepy.bluepy_utils import ble_scan_bluepy
from mat.ble.bluepy.cc26x2r_logger_controller import LoggerControllerCC26X2R
from mat.ble.bluepy.cc26x2r_utils import utils_logger_is_cc26x2r, utils_logger_is_cc26x2r_new
from mat.ble.bluepy.moana_logger_controller import utils_logger_is_moana, LoggerControllerMoana
from mat.ble.bluepy.rn4020_logger_controller import LoggerControllerRN4020
from mat.ble.bluepy.rn4020_utils import utils_logger_is_rn4020
from mat.ddh_shared import send_ddh_udp_gui as _u, ddh_get_json_mac_dns, \
    get_dl_folder_path_from_mac, \
    get_dds_aws_has_something_to_do_flag, \
    get_dds_folder_path_macs_black, ddh_get_macs_from_json_file
from mat.dds_states import *
from settings import ctx
from settings.ctx import hook_ble_purge_this_mac_dl_files_folder, \
    hook_ble_purge_black_macs_on_boot, macs_color_create_folder, ble_flag_dl, ble_un_flag_dl
from dds.logs import lg_dds as lg


TIME_IGNORE_TOO_ERROR = 600
TIME_IGNORE_ONE_ERROR = 30
g_logger_errors = {}
g_ts_scan_banner = 0


def ble_show_monitored_macs():
    mm = ddh_get_macs_from_json_file()
    for i in mm:
        lg.a('debug: monitored mac {}'.format(i))


def _print_scan_banner():
    global g_ts_scan_banner
    now = time.perf_counter()
    _first_banner = g_ts_scan_banner == 0
    _expired_banner = now > g_ts_scan_banner + 300
    if _first_banner or _expired_banner:
        g_ts_scan_banner = now + 300
        lg.a('scanning ...')


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
    print('{} has {} files for us'.format(lc.address, len(ff)))
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


def ble_debug_hooks_at_boot():
    if hook_ble_purge_black_macs_on_boot:
        lg.a('debug: HOOK_PURGE_BLACK_MACS_ON_BOOT')
        p = pathlib.Path(get_dds_folder_path_macs_black())
        shutil.rmtree(str(p), ignore_errors=True)
        macs_color_create_folder()


def _ble_set_aws_flag():
    flag = get_dds_aws_has_something_to_do_flag()
    pathlib.Path(flag).touch()
    lg.a('debug: flag ddh_aws_has_something_to_do set')


def _ble_scan(h) -> dict:
    _u(STATE_DDS_BLE_SCAN)
    li = {}

    _print_scan_banner()
    time.sleep(.1)

    try:
        # {<mac_1>: 'LOGGER_TYPE', ...}
        sr = ble_scan_bluepy(h)

        for i in sr:
            if not type(i.rawData) is bytes:
                # skips problems with Apple devices
                continue

            # debug
            # print(i.addr.lower(), i.rawData)

            for n in (
                    b'DO-3',
                    b'DO-2',
                    b'DO-1',
                    b'MOANA',
                    b'MATP-2W',
                    b'MATP-2WA'):
                if i.rawData.count(n):
                    li[i.addr.lower()] = n.decode()

    except (ble.BTLEException, Exception) as e:
        _u(STATE_DDS_BLE_HARDWARE_ERROR)
        lg.a('error: exception -> {}'.format(e))
        li = {}

    finally:
        return li


def _ble_interact_w_logger(mac, info: str, h, g):

    # debug
    # l_d_('forcing query of hardcoded mac')
    # hc_mac = '60:77:71:22:c8:6f'
    # hc_info = 'DO-2'
    # mac = hc_mac
    # info = hc_info

    # debug: delete THIS logger's existing files
    if hook_ble_purge_this_mac_dl_files_folder:
        lg.a('debug: HOOK_PURGE_THIS_MAC_DL_FILES_FOLDER {}'.format(mac))
        p = pathlib.Path(get_dl_folder_path_from_mac(mac))
        shutil.rmtree(str(p), ignore_errors=True)

    # bunch of variables needed
    lc = None
    lat, lon, dt = g
    sn = ddh_get_json_mac_dns(mac)
    _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD, sn))
    rv = 0
    s = 'querying sensor {} / mac {}'
    lg.a(s.format(sn, mac))

    try:
        if utils_logger_is_rn4020(mac, info):
            print('----> rn4020')
            # lc = LoggerControllerRN4020(mac, h)
            # utils_ble_rn4020_interact(lc, g)

        elif utils_logger_is_moana(mac, info):
            print('----> moana')
            # todo > copy this from moana in DDH
            # lc = LoggerControllerMoana(mac)
            # utils_ble_moana_interact(lc)

        elif utils_logger_is_cc26x2r_new(mac, info):
            print('-----> doX')
            # lc = LoggerControllerCC26X2R(mac, h, what='DO-4')
            # utils_ble_cc26x2r_interact(lc, g)

        else:
            e = 'error: unknown logger, mac {} info {}'
            lg.a(e.format(mac, info))

    # except AppBLEException as ex:
    #     --------------------------
    #     ble_die() -> reaches here
    #     --------------------------
        # e = '[ BLE] error: app exception {} -> {}'
        # lg.a(e.format(ex, traceback.format_exc()))
        # rv = 1

    except (ble.BTLEException, Exception) as ex:
        e = '[ BLE] error: wireless exception {} -> {}'
        lg.a(e.format(ex, traceback.format_exc()))
        rv = 1
        sns_notify_ble_scan_exception(lat, lon)

    finally:
        if lc:
            lc.close()
        if rv == 0:
            _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_OK, sn))
            h = 'history/add&{}&ok&{}&{}&{}'
        else:
            _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_ERROR, sn))
            h = 'history/add&{}&error&{}&{}&{}'
        _u(h.format(sn, lat, lon, dt))

        # track logger errors
        _add_logger_errors_to_sns_if_any(rv, mac, lat, lon)

        # todo > maybe remove this
        # hack for loggers on their way to fail 5 times
        if rv:
            v = g_logger_errors[mac] + 1
            if v == 2 and utils_logger_is_cc26x2r(mac, info):
                ctx.req_reset_mac_cc26x2r = mac
                lg.a('debug: set flag req_reset_mac_cc26x2r')
        else:
            g_logger_errors[mac] = 0
        return rv


def _add_logger_errors_to_sns_if_any(rv, mac, lat, lon):
    if rv == 0:
        rm_mac_black(mac)
        rm_mac_orange(mac)
        add_mac_black(mac)
        return

    if mac not in g_logger_errors:
        g_logger_errors[mac] = 1
        rm_mac_black(mac)
        add_mac_orange(mac)
        return

    v = g_logger_errors[mac] + 1
    if v > 5:
        v = 5

    if v == 5:
        sns_notify_logger_error(mac, lat, lon)
        rm_mac_orange(mac)
        add_mac_black(mac)
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_ERROR, mac))
    else:
        rm_mac_orange(mac)
        add_mac_orange(mac)
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_WARNING, mac))


def ble_loop(macs_mon, _lat, _lon, _dt, _h, _h_desc):

    _u('{}/{}'.format(STATE_DDS_BLE_ANTENNA, _h_desc))

    det = _ble_scan(0)
    b = macs_black()
    o = macs_orange()

    for mac, model in det.items():
        if mac not in macs_mon:
            continue
        if is_mac_in_black(mac, b):
            continue
        if is_mac_in_orange(mac, o):
            continue

        # MAC passed all filters, work with it
        g = (_lat, _lon, _dt)
        ble_flag_dl()
        rv = _ble_interact_w_logger(mac, model, _h, g)
        ble_un_flag_dl()
        if rv == 0:
            _ble_set_aws_flag()
