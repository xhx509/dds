import pathlib
import shutil
import traceback

import bluepy.btle as ble
import time
from dds.logs import l_e_, l_d_
from dds.macs import macs_black, macs_orange
from dds.utils_ble_cc26x2r import utils_ble_cc26x2r_interact
from dds.utils_ble_lowell import AppBLEException
from dds.utils_ble_moana import utils_ble_moana_interact
from dds.utils_ble_rn4020 import utils_ble_rn4020_interact
from mat.ble.bluepy.bluepy_utils import ble_scan_bluepy
from mat.ble.bluepy.cc26x2r_logger_controller import LoggerControllerCC26X2R
from mat.ble.bluepy.cc26x2r_utils import utils_logger_is_cc26x2r
from mat.ble.bluepy.moana_logger_controller import utils_logger_is_moana, LoggerControllerMoana
from mat.ble.bluepy.rn4020_logger_controller import LoggerControllerRN4020
from mat.ble.bluepy.rn4020_utils import utils_logger_is_rn4020
from mat.ddh_shared import send_ddh_udp_gui as _u, ddh_get_json_mac_dns, get_dl_folder_path_from_mac
from settings.ctx import hook_purge_this_mac_dl_files_folder


TIME_IGNORE_TOO_ERROR = 600
TIME_IGNORE_ONE_ERROR = 30


# todo > create file flag to force AWS service to update

# def utils_ble_logger_download_show_result(rv, mac):
#     m_r = DbMacs(ctx.db_macs)
#     m_r.db_get()
#     if rv:
#         core_set_state(STATE_BLE_DL_OK)
#         j = ctx.file_ddh_json
#         f_t = json_get_forget_time_secs(j)
#         # ------------------------------------------
#         # to black list as good, remove from orange
#         # ------------------------------------------
#         m_r.del_record_by_mac(mac)
#         till = int(time.time()) + f_t
#         m_r.add_black(mac, till, 0)
#
#         # AWS has something to do
#         ctx.aws_do = True
#         return
#
#     # ------------
#     # went south
#     # ------------
#     core_set_state(STATE_BLE_DL_WARNING)
#     r = m_r.get_retries_by_mac(mac)
#     r = 1 if not r else r + 1 if r < 5 else 5
#
#     if r == 5:
#         # -----------------------------------------
#         # too many errors -> to black list for bad
#         # remove it from orange
#         # -----------------------------------------
#         m_r.del_record_by_mac(mac)
#         till = int(time.time()) + TIME_IGNORE_TOO_ERROR
#         m_r.add_black(mac, till, 0)
#         e = '[ BLE ] max errors by {} -> black-list for {} secs'
#         e = e.format(mac, TIME_IGNORE_TOO_ERROR)
#         l_e_(e)
#         core_set_state(STATE_BLE_DL_ERROR)
#
#         # ----------------------------------
#         # to notify via SNS
#         # ----------------------------------
#         if ctx.sns_en:
#             now = str(datetime.datetime.now())
#             j = ctx.file_ddh_json
#             vessel = json_get_vessel_name(j)
#             e = 'mac {} vessel {} time {}'
#             e = e.format(mac, vessel, now)
#             db = DbSNS(ctx.db_sns)
#             db.db_get()
#             t = time.time()
#             db.add_logger(mac, t, e, 0)
#         return
#
#     # ----------------------------------
#     # not final error but + 1 at orange
#     # ----------------------------------
#     till = int(time.time()) + TIME_IGNORE_ONE_ERROR
#     m_r.update_by_color(mac, till, r, 'orange')
#     e = '[ BLE ] one error by {} -> orange-list as r = {} for {} secs'
#     e = e.format(mac, r, TIME_IGNORE_ONE_ERROR)
#     l_e_(e)


def _ble_scan(h) -> dict:
    _u('state_scan/')
    li = {}

    try:
        time.sleep(.1)
        # {<mac_1>: 'LOGGER_TYPE', ...}
        sr = ble_scan_bluepy(h)
        for i in sr:
            if not type(i.rawData) is bytes:
                continue
            for n in (b'DO-2', b'DO-1', b'MOANA', b'MATP-2W', b'MATP-2WA'):
                if i.rawData.count(n):
                    li[i.addr.lower()] = n.decode()

    except (ble.BTLEException, Exception) as e:
        _u('state_ble_hardware_error/')
        l_e_('exception -> {}'.format(e))

    finally:
        return li


def _ble_interact_w_logger(mac, info: str, h, g):

    # debug
    hc_mac = '60:77:71:22:c8:6f'
    mac = hc_mac
    hc_info = 'DO-2'
    info = hc_info

    # debug: delete THIS logger's existing files
    if hook_purge_this_mac_dl_files_folder:
        l_d_('[ BLE ] debug hook -> rm files {}'.format(mac))
        _pre_rm_path = pathlib.Path(get_dl_folder_path_from_mac(mac))
        shutil.rmtree(str(_pre_rm_path), ignore_errors=True)

    lc = None
    lat, lon, dt = g
    sn = ddh_get_json_mac_dns(mac)
    _u('state_download/{}'.format(sn))
    rv = 0

    try:
        if utils_logger_is_rn4020(mac, info):
            lc = LoggerControllerRN4020(mac, h)
            utils_ble_rn4020_interact(lc, g)

        elif utils_logger_is_moana(mac, info):
            lc = LoggerControllerMoana(mac)
            utils_ble_moana_interact(lc)

        elif utils_logger_is_cc26x2r(mac, info):
            lc = LoggerControllerCC26X2R(mac, h, what=info)
            utils_ble_cc26x2r_interact(lc, g)

    except AppBLEException as ex:
        # --------------------------
        # ble_die() -> reaches here
        # --------------------------
        e = '[ BLE] app exception {} -> {}'
        l_e_(e.format(ex, traceback.format_exc()))
        rv = 1

    except (ble.BTLEException, Exception) as ex:
        e = '[ BLE] wireless exception {} -> {}'
        l_e_(e.format(ex, traceback.format_exc()))
        rv = 1

    finally:
        if lc:
            lc.close()
        if rv == 0:
            _u('state_download_ok/{}'.format(sn))
            h = 'history/add&{}&ok&{}&{}&{}'
        else:
            _u('state_download_error/{}'.format(sn))
            h = 'history/add&{}&error&{}&{}&{}'
        _u(h.format(sn, lat, lon, dt))


def ble_loop(_lat, _lon, _h, _d):

    _u('ble_antenna_is/{}'.format(_d))

    det = _ble_scan(0)
    b = macs_black()
    o = macs_orange()
    for mac, model in det.items():
        if mac in b:
            continue
        if mac in o:
            continue

        g = (_lat, _lon)
        _ble_interact_w_logger(mac, model, _h, g)
