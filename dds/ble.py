import os
import pathlib
import shutil
import traceback
import bluepy.btle as ble
import time
import asyncio
from bleak import BleakScanner
from dds.macs import macs_black, macs_orange, rm_mac_black, rm_mac_orange, add_mac_orange, add_mac_black, \
    is_mac_in_black, is_mac_in_orange
from dds.sns import sns_notify_logger_error, sns_notify_ble_scan_exception
from dds.utils import print_ble_scan_banner
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
    hook_ble_purge_black_macs_on_boot, macs_create_color_folders
from dds.logs import lg_dds as lg


TIME_IGNORE_TOO_ERROR = 600
TIME_IGNORE_ONE_ERROR = 30
g_logger_errors = {}


def ble_show_monitored_macs():
    mm = ddh_get_macs_from_json_file()
    for i in mm:
        lg.a('debug: monitored mac {}'.format(i))


def ble_set_last_haul(fol, s):
    # todo > implement this as glog.glog[-1]
    pass


def ble_apply_debug_hooks_at_boot():
    if hook_ble_purge_black_macs_on_boot:
        lg.a('debug: HOOK_PURGE_BLACK_MACS_ON_BOOT')
        p = pathlib.Path(get_dds_folder_path_macs_black())
        shutil.rmtree(str(p), ignore_errors=True)
        macs_create_color_folders()


def _ble_set_aws_flag():
    flag = get_dds_aws_has_something_to_do_flag()
    pathlib.Path(flag).touch()
    lg.a('debug: flag ddh_aws_has_something_to_do set')


def _ble_logger_result_to_sns(rv, mac, lat, lon):
    if rv == 0:
        return

    sns_notify_logger_error(mac, lat, lon)


def _ble_logger_result_to_macs(rv, mac, lat, lon):
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

    g_logger_errors[mac] += 1
    v = g_logger_errors[mac]
    if v > 5:
        v = 5
        g_logger_errors[mac] = 0

    if v == 5:
        rm_mac_orange(mac)
        add_mac_black(mac)
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_ERROR, mac))
    else:
        rm_mac_orange(mac)
        add_mac_orange(mac)
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_WARNING, mac))


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

    # variables
    rv = 0
    lat, lon, dt = g
    sn = ddh_get_json_mac_dns(mac)
    _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD, sn))
    lg.a('querying sensor {} / mac {}'.format(sn, mac))

    try:
        if utils_logger_is_rn4020(mac, info):
            print('----> rn4020')
            # lc = LoggerControllerRN4020(mac, h)
            # utils_ble_rn4020_interact(lc, g)

        elif utils_logger_is_moana(mac, info):
            # todo > copy this from moana in DDH
            # lc = LoggerControllerMoana(mac)
            # utils_ble_moana_interact(lc)

        elif utils_logger_is_cc26x2r_new(mac, info):
            print('-----> doX')
            # lc = LoggerControllerCC26X2R(mac, h, what='DO-4')
            # utils_ble_cc26x2r_interact(lc, g)

        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_OK, sn))
        h = 'history/add&{}&ok&{}&{}&{}'

    # todo > change this for bleak exceptions
    except (ble.BTLEException, Exception) as ex:
        e = 'error: exception {} -> {}'
        lg.a(e.format(ex, traceback.format_exc()))
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_ERROR, sn))
        h = 'history/add&{}&error&{}&{}&{}'
        rv = 1

    finally:
        _u(h.format(sn, lat, lon, dt))
        _ble_logger_result_to_sns(rv, mac, lat, lon)
        _ble_logger_result_to_macs(rv, mac, lat, lon)
        return rv


def _ble_is_supported_logger(s, mac):
    # lt: logger types
    lt = ['DO-2', 'DO-1', 'MOANA', 'MAT-2W']
    for t in lt:
        if t in s:
            _ = '{} supported logger type, mac {}'
            print(_.format(s, mac))
            return True


# todo: do the hci thing here for bleak
async def _ble_scan(h) -> tuple:
    """ returns {mac: DO-X, mac2: MATP-2W}, ... """

    time.sleep(.1)
    print_ble_scan_banner()
    _u(STATE_DDS_BLE_SCAN)
    li = {}
    rv = 0

    try:
        for d in await BleakScanner.discover(timeout=5):
            if _ble_is_supported_logger(d.name, d.address):
                li[d.address.lower()] = d.name
        return rv, li

    except (ble.BTLEException, Exception) as e:
        _u(STATE_DDS_BLE_HARDWARE_ERROR)
        lg.a('error: exception -> {}'.format(e))
        rv = 1
        return rv, {}


async def ble_loop(macs_mon, _lat, _lon, _dt, _h, _h_desc):

    _u('{}/{}'.format(STATE_DDS_BLE_ANTENNA, _h_desc))
    b = macs_black()
    o = macs_orange()

    rv, det = await _ble_scan(0)
    if rv:
        # todo > pass antenna to this exception
        sns_notify_ble_scan_exception(_lat, _lon)
        return

    for mac, model in det.items():
        if mac not in macs_mon:
            continue
        if is_mac_in_black(mac, b):
            continue
        if is_mac_in_orange(mac, o):
            continue

        # MAC passed all filters, work with it
        g = (_lat, _lon, _dt)
        rv = _ble_interact_w_logger(mac, model, _h, g)
        if rv == 0:
            _ble_set_aws_flag()
