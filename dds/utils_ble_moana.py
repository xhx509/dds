import os
import time
from dds.utils_ble_lowell import ble_die, ble_ok, utils_ble_set_last_haul, AppBLEException
from mat.ddh_shared import get_dl_folder_path_from_mac
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import STATE_DDS_REQUEST_PLOT
from dds.logs import lg_dds as lg


def _ble_moana_open(lc) -> bool:
    for i in range(3):
        try:
            if lc.open():
                return True
        except AppBLEException:
            time.sleep(1)
    return False


def _ble_moana_get_size(lc) -> int:
    for i in range(3):
        try:
            f_size = lc.file_info_get_size()
            if f_size:
                return f_size
        except AppBLEException:
            time.sleep(1)
    ble_die('failed getting file size')


def utils_ble_moana_interact(lc):

    if not _ble_moana_open(lc):
        ble_die('cannot connect {}'.format(lc.mac))

    # -----------------------------------
    # authentication sometimes fails
    # -----------------------------------
    lg.a('BLE error: authenticating to logger')
    if not lc.auth():
        ble_die('auth')
    ble_ok('authentication OK')
    if not lc.time_sync():
        ble_die('time_sync')
    ble_ok('time synced OK')

    # -----------------------------------
    # get metadata of file inside moana
    # -----------------------------------
    f_name = ''
    for i in range(3):
        f_name = lc.file_info()
        if f_name:
            break
        if i == 2 and not f_name:
            ble_die('file_info')
        time.sleep(1)

    # --------------------
    # download moana file
    # --------------------
    fol = get_dl_folder_path_from_mac(lc.mac)
    try:
        os.mkdir(fol)
    except OSError:
        pass

    f_size = _ble_moana_get_size(lc)
    s = 'BLE #1, getting file {}, size {}'
    lg.a(s.format(f_name, f_size))
    d1 = lc.file_get(f_size)

    f_size = _ble_moana_get_size(lc)
    s = 'BLE #2, getting file {}, size {}'
    lg.a(s.format(f_name, f_size))
    d2 = lc.file_get(f_size)

    # ---------------------------------------------
    # moana CRC is weird, we just download file
    # twice and compare the data section
    # ---------------------------------------------
    i = d1.index(b'\x03')
    if d1[i:] != d2[i:]:
        ble_die('file_pseudo_crc')
    lg.a('BLE moana file download twice and OK')
    path = lc.file_save(fol, d1)
    if not path:
        ble_die('file_save')

    # ------------------------------------
    # conversion of the file inside moana
    # ------------------------------------
    lg.a('BLE converting file {}'.format(f_name))
    prefix_cnv = lc.file_cnv(path, fol, len(d1))
    if not prefix_cnv:
        ble_die('file conversion')

    # ----------------------------------------
    # DEBUG: comment for repetitive downloads
    # ----------------------------------------
    # time.sleep(1)
    # lc.file_clear()

    # for last haul application
    utils_ble_set_last_haul(fol, prefix_cnv)

    # -----------------------------------
    # PLOT only if we got some files
    # -----------------------------------
    _u('{}/{}'.format(STATE_DDS_REQUEST_PLOT, lc.mac))

    return True
