import os
import socket
import time
from dds.logs import l_i_
from dds.utils_ble_lowell import ble_die, ble_ok, utils_ble_set_last_haul
from mat.ddh_shared import get_dl_folder_path_from_mac


def _progress_bar_poor(v):
    _sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sk.sendto(str(v).encode(), ('127.0.0.1', 12349))


def utils_ble_moana_interact(lc):

    if not lc.open():
        ble_die('cannot connect {}'.format(lc.mac))

    # -----------------------------------
    # authentication sometimes fails
    # -----------------------------------
    l_i_('[ BLE ] authenticating to logger')
    if not lc.auth():
        ble_die('auth')
    ble_ok('authentication OK')
    if not lc.time_sync():
        ble_die('time_sync')
    ble_ok('time synced OK')

    # -----------------------------------
    # get metadata of file inside moana
    # -----------------------------------
    filename = ''
    for i in range(3):
        filename = lc.file_info()
        if filename:
            break
        if i == 2 and not filename:
            ble_die('file_info')
        time.sleep(1)

    # ---------------------------------------------
    # moana CRC is weird, we just download file
    # twice and compare the data section
    # ---------------------------------------------
    fol = get_dl_folder_path_from_mac(lc.mac)
    try:
        os.mkdir(fol)
    except OSError:
        pass
    l_i_('[ BLE ] #1, getting file {}'.format(filename))
    _progress_bar_poor(20)
    data = lc.file_get()
    l_i_('[ BLE ] #2, getting file {}'.format(filename))
    lc.file_info()
    data2 = lc.file_get()
    _progress_bar_poor(100)
    i = data.index(b'\x03')
    data_section_equal = data[i:] == data2[i:]
    if not data_section_equal:
        ble_die('file_pseudo_crc')

    name = lc.file_save(fol, data)
    if not name:
        ble_die('file_save')

    # -----------------------------------
    # conversion of the file inside moana
    # -----------------------------------
    l_i_('[ BLE ] converting file...')
    prefix_cnv = ''
    for i in range(3):
        prefix_cnv = lc.file_cnv(name, fol, len(data))
        if i == 2 and not prefix_cnv:
            ble_die('file conversion')
        time.sleep(1)

    # --------------------------------------
    # comment on debug for repetitive tasks
    # --------------------------------------
    time.sleep(1)
    lc.file_clear()

    # for last haul application
    utils_ble_set_last_haul(fol, prefix_cnv)

    # -----------------------------------
    # PLOT only if we got some files
    # -----------------------------------
    # back['plt']['dl'] = lc.mac

    return True
