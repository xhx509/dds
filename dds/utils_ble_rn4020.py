import os
import time

from dds.utils_ble_lowell import utils_ble_build_files_to_download_as_dict, ble_ok, ble_die, ble_li_sws, ble_li_btc, \
    ble_li_time_sync, ble_li_ls_all, ble_li_run, utils_ble_set_last_haul
from mat.ddh_shared import send_ddh_udp_gui as _u
from dds.logs import l_e_
from mat.ddh_shared import get_dl_folder_path_from_mac
from mat import data_file_factory
from mat.dds_states import STATE_DDS_REQUEST_PLOT


def _get_files_rn4020(lc, ls):

    name_n_size = utils_ble_build_files_to_download_as_dict(lc, ls)
    if not name_n_size:
        return True, {}

    # ---------------------------------------
    # XMODEM GET (download) files one by one
    # feed the dog based on file size
    # ---------------------------------------
    b_left = sum([int(i) for i in name_n_size.values()])
    dl_ones_ok = {}
    for name, size in name_n_size.items():
        ble_ok('getting file {}, {} bytes'.format(name, size))
        data = lc.ble_cmd_get(name, size)
        if not data:
            e = '[ BLE ] cannot get {}, size {}'
            ble_die(e.format(name, size))
            return False, dl_ones_ok
        path = get_dl_folder_path_from_mac(lc.address) / name
        with open(str(path), 'wb+') as f:
            f.write(data)

        # --------------------------
        # RN4020 -> delete the file
        # --------------------------
        time.sleep(3)
        if not lc.ble_cmd_del(name):
            e = '[ BLE ] cannot delete {}, size {}'
            ble_die(e.format(name, size))
            return False, dl_ones_ok

        # ------------------------------------
        # file: CRC is always OK from x-modem
        # ------------------------------------
        ble_ok('100% got {}'.format(name))
        dl_ones_ok[name] = size
        b_left -= size

    # ----------------
    # display success
    # ----------------
    ble_ok('almost done')
    return len(name_n_size) == len(dl_ones_ok), dl_ones_ok


def utils_ble_rn4020_interact(lc, g):

    if not lc.open():
        ble_die('cannot connect {}'.format(lc.address))

    time.sleep(.5)
    ble_li_sws(lc, g)
    time.sleep(.5)
    ble_li_btc(lc)
    time.sleep(.5)
    ble_li_time_sync(lc)
    time.sleep(.5)

    ls = ble_li_ls_all(lc)
    time.sleep(1)

    rv, dl = _get_files_rn4020(lc, ls)
    time.sleep(.5)

    if rv:
        time.sleep(.5)
        ble_li_run(lc)
    else:
        l_e_('error downloading files')
        return

    # ----------------------------------
    # RN4020 renaming local files trick
    # ----------------------------------
    fol = get_dl_folder_path_from_mac(lc.address)
    for k, v in dl.items():
        if not k.endswith('.lid'):
            continue

        # -----------------------------------
        # grab the file's CLK header section
        # -----------------------------------
        src = '{}/{}'.format(fol, k)
        _ = data_file_factory.load_data_file(src)
        t = _.header().tag('CLK')
        t = t.replace(':', '')
        t = t.replace('-', '')
        t = t.replace(' ', '')
        dst = src.replace('.lid', '')
        dst = '{}_{}.lid'.format(dst, t)
        os.rename(src, dst)

        # ---------------------------
        # for last haul application
        # ---------------------------
        prefix = dst.replace('.lid', '')
        utils_ble_set_last_haul(fol, prefix)

    # -----------------------------------
    # PLOT only if we got some lid files
    # -----------------------------------
    if any(k.endswith('lid') for k in dl.keys()):
        _u('{}/{}'.format(STATE_DDS_REQUEST_PLOT, lc.address))

    return True
