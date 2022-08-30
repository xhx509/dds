from dds.sns import sns_notify_dissolved_oxygen_zeros
from dds.utils_ble_lowell import *
from mat.crc import calculate_local_file_crc
from mat.dds_states import STATE_DDS_BLE_DOWNLOAD_SLOW, STATE_DDS_BLE_DEPLOY_FALLBACK, STATE_DDS_REQUEST_PLOT, \
    STATE_DDS_BLE_DOWNLOAD
from mat.utils import linux_is_rpi3
from settings import ctx
from mat.ddh_shared import send_ddh_udp_gui as _u, ddh_get_json_mac_dns, get_dl_folder_path_from_mac
from settings.ctx import hook_ble_gdo_dummy_measurement, hook_ble_create_dummy_file
from dds.logs import lg_dds as lg
import subprocess as sp


def _cc26x2r_rm_null_files(lc, ls):

    for name, size in ls.items():
        if name.endswith('lid') and int(size) == 0:
            lg.a("BLE deleting 0-bytes file {}".format(name))
            rv = lc.ble_cmd_del(name)
            if not rv:
                return False
            time.sleep(3)
    return True


def _cc26x2r_deploy(lc, ls: dict, g):

    # ----------------------------
    # always ensure wake-up mode
    # ----------------------------
    if not lc.ble_cmd_wak_ensure('on'):
        ble_die('wake CMD failed')
    ble_ok('WAK ON')

    # ---------------------------------------------------
    # RE-DEPLOY DECISION based on MAT.cfg present or not
    # ---------------------------------------------------
    if 'MAT.cfg' in ls.keys():
        lg.a('BLE interact -> re_deploy OK with existing MAT.cfg ')
        return

    # ------------------------------------------------
    # missing MAT.cfg file, we need a whole re-deploy
    # ------------------------------------------------
    _u(STATE_DDS_BLE_DEPLOY_FALLBACK)
    lg.a('BLE warning: logger has no MAT.cfg, providing one')
    if not lc.ble_cmd_stp():
        ble_die('error in re-deploy STP')
    if not lc.ble_cmd_stm():
        ble_die('error in re-deploy STM')
    # if not lc.ble_cmd_frm():
    #     ble_die('error in re-deploy FRM')
    sn = ddh_get_json_mac_dns(lc.address)
    sn = 'SN{}'.format(sn[:7])
    if not lc.ble_cmd_wli(sn):
        ble_die('error in re-deploy SN')
    if not lc.ble_cmd_wli('CA1234'):
        ble_die('error in re-deploy CA')
    if not lc.ble_cmd_wli('BA8007'):
        ble_die('error in re-deploy BA')
    if not lc.ble_cmd_wli('MA1234ABC'):
        ble_die('error in re-deploy MA')
    if not lc.ble_cmd_wak_ensure('on'):
        ble_die('error in re-deploy WAK')

    # -----------------
    # send CFG command
    # -----------------
    c = {}
    c_dict = {
        'DO-1': ctx.mat_cfg_do1_fallback,
        'DO-2': ctx.mat_cfg_do2_fallback,
        'DO-4': ctx.mat_cfg_do2_fallback
    }
    try:
        c = c_dict[lc.what]
    except KeyError:
        ble_die('fallback MAT cfg dictionary error')

    if not lc.ble_cmd_cfg(c):
        ble_die('error in logger re-deploy command')
    s = 'BLE interact -> re_deploy OK w/ {} fallback MAT.cfg'
    lg.a(s.format(lc.what))


def _cc26x2r_dwg_files(lc, ls) -> tuple:
    ls_d = utils_ble_build_files_to_download_as_dict(lc, ls)
    if not ls_d:
        return True, {}

    # -----------------------------------------
    # iterate downloading all the files
    # -----------------------------------------
    b_left = sum([int(i) for i in ls_d.values()])
    dl_ones_ok = {}

    for name, size in ls_d.items():
        # ------------
        # DWG command
        # ------------
        ble_ok('downloading file {}, {} bytes'.format(name, size))
        if not lc.ble_cmd_dwg(name):
            lg.a('BLE error when downloading {}'.format(name))
            return False, dl_ones_ok

        # -----------------------------------
        # 3 DWL command retries per file :)
        # -----------------------------------
        time.sleep(1)
        path = get_dl_folder_path_from_mac(lc.address) / name
        for i in range(3):
            _t = time.perf_counter()
            data = lc.ble_cmd_dwl(size)
            _t = time.perf_counter() - _t
            lg.a('BLE speed {:.2f} KB/s'.format((size / _t) / 1000))
            if data:
                with open(str(path), 'wb+') as f:
                    f.write(data)
                break
            if i == 2:
                return False, dl_ones_ok
            lg.a('BLE warning: re-trying download {}'.format(name))
            time.sleep(1)

        # ---------------------------------
        # check file remote and local CRC
        # ---------------------------------
        time.sleep(1)
        crc = lc.ble_cmd_crc(name)
        l_crc = calculate_local_file_crc(path)
        if crc != l_crc:
            e = 'BLE error CRC local {} VS remote {} for {}'
            lg.a(e.format(l_crc, crc, name))
            if os.path.exists(path):
                s = 'warning: BLE removing local file {} with bad CRC'
                lg.a(s.format(path))
                os.remove(path)
            return False, dl_ones_ok

        # ------------------------------------
        # delete single file remotely
        # -------------------------------------
        time.sleep(1)
        ble_ok('100% downloaded {}'.format(name))
        if not lc.ble_cmd_del(name):
            lg.a('BLE error when deleting file {}'.format(name))
            return False, dl_ones_ok
        dl_ones_ok[name] = size
        b_left -= size

        # ---------------------------
        # for last haul application
        # ---------------------------
        fol = get_dl_folder_path_from_mac(lc.address)
        prefix = name.replace('.lid', '')
        utils_ble_set_last_haul(fol, prefix)

    # ----------------
    # display success
    # ----------------
    return len(ls_d) == len(dl_ones_ok), dl_ones_ok


def utils_ble_cc26x2r_interact(lc, g):

    # -----------------------------
    # battery, stop and time sync
    # ------------------------------
    if not lc.open():
        ble_die('cannot connect {}'.format(lc.address))

    sn = ddh_get_json_mac_dns(lc.address)

    ble_li_gfv(lc)
    ble_li_bat(lc)
    ble_li_sws(lc, g)
    ble_li_time_sync(lc)

    # debug hook MTS
    if hook_ble_create_dummy_file:
        ble_li_mts(lc)

    # --------------------------------------
    # listing files in cc26x2-based logger
    # --------------------------------------
    ls = ble_li_ls_all(lc)

    # ---------------------------------------------------------------
    # remote clean-up for files we already have or with size 0-bytes
    # ---------------------------------------------------------------
    ble_li_rm_already_have(lc, ls)
    rv = _cc26x2r_rm_null_files(lc, ls)
    if not rv:
        lg.a('BLE error when clean-up 0-bytes files in logger')
        return False

    # --------------------------------------
    # download files in cc26x2-based logger
    # --------------------------------------
    # todo > do this better
    c = '/home/kaz/PycharmProjects/ddh_tools/set_linux_ble_conn_parameters.sh'
    if linux_is_rpi3():
        lg.a('BLE debug: tuning connection parameters to slow mode')
        rv = sp.run([c, 'slow'], stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        lg.a('BLE debug: tuning connection parameters to fast mode')
        rv = sp.run([c, 'fast'], stdout=sp.PIPE, stderr=sp.PIPE)
    print(rv.stdout)

    rv, dl = _cc26x2r_dwg_files(lc, ls)
    if not rv:
        _u('{}/{}'.format(STATE_DDS_BLE_DOWNLOAD, sn))
        lg.a('BLE error when downloading files')

    # --------------------------------
    # re-deploy logger cc26x2r
    # --------------------------------
    ble_ok('almost done')
    rv = ble_li_gdo(lc)
    if not rv:
        lat, lon, _ = g
        sns_notify_dissolved_oxygen_zeros(lc.address, lat, lon)
        ble_die('error ble_li_gdo')

    _cc26x2r_deploy(lc, ls, g)
    ble_li_rws(lc, g)

    # -----------------------------------
    # PLOT only if we got some lid files
    # -----------------------------------
    if any(k.endswith('lid') for k in dl.keys()):
        _u('{}/{}'.format(STATE_DDS_REQUEST_PLOT, lc.address))

    return True
