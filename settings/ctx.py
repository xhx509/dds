import glob
import os
import pathlib

from dds.utils_ble_logs import l_i_, l_d_
from dds.macs import macs_black, macs_orange
from mat.ddh_shared import send_ddh_udp_gui, get_ddh_disabled_ble_file_flag, dds_get_json_moving_speed, \
    ddh_get_json_app_type, get_ddh_app_override_file_flag, get_ddh_black_macs_purge_file_flag, \
    get_dds_is_ble_downloading_flag
from mat.dds_states import STATE_DDS_BLE_DISABLED, STATE_DDS_BLE_APP_GPS_ERROR_SPEED
from mat.utils import linux_is_rpi
import subprocess as sp


_u = send_ddh_udp_gui


plt_units_temp = None
plt_units_depth = None
span_dict = None


# pusher
push_en = False


# AWS / SNS: enabled or not
aws_en = True
aws_do = True
sns_en = True


# BLE: enabled or not + switch capability
ble_en = True
sw_ble_en = True
req_reset_mac_cc26x2r = ''


# cell shield: present or not
cell_shield_en = True


# debug hooks :)
hook_ntp_force_error = False
hook_gps_dummy_measurement = not linux_is_rpi()
hook_gps_error_measurement_forced = False
hook_ble_error_forced = False
hook_ble_gdo_dummy_measurement = True
hook_ble_purge_black_macs_on_boot = True
hook_ble_purge_this_mac_dl_files_folder = False
hook_ble_create_dummy_file = True


# contains process handlers
proc_aws = None
proc_cnv = None


# to re-deploy
mat_cfg_do1_fallback = {
        "DFN": "fal_do1",
        "TMP": 0, "PRS": 0,
        "DOS": 1, "DOP": 1, "DOT": 1,
        "TRI": 10, "ORI": 10, "DRI": 900,
        "PRR": 1,
        "PRN": 1,
        "STM": "2012-11-12 12:14:00",
        "ETM": "2030-11-12 12:14:20",
        "LED": 1
}
mat_cfg_do2_fallback = {
        "DFN": "fal_do2",
        "TMP": 0, "PRS": 0,
        "DOS": 1, "DOP": 1, "DOT": 1,
        "TRI": 10, "ORI": 10, "DRI": 900,
        "PRR": 1,
        "PRN": 1,
        "STM": "2012-11-12 12:14:00",
        "ETM": "2030-11-12 12:14:20",
        "LED": 1
}


def macs_color_create_folder():
    r = 'macs'
    os.makedirs(r, exist_ok=True)
    r = 'macs/black'
    os.makedirs(r, exist_ok=True)
    r = 'macs/orange'
    os.makedirs(r, exist_ok=True)


def sns_create_folder():
    r = 'sns'
    os.makedirs(r, exist_ok=True)


def macs_color_show_at_boot():
    b = macs_black()
    o = macs_orange()
    l_i_('[ BLE ] boot macs_black  = {}'.format(b))
    l_i_('[ BLE ] boot macs_orange = {}'.format(o))


def op_conditions_met(knots) -> bool:

    flag = get_ddh_black_macs_purge_file_flag()
    if os.path.isfile(flag):
        l_d_('[ BLE ] flag macs purge was set')
        for f in glob.glob('macs/black/*'):
            os.unlink(f)
        for f in glob.glob('macs/orange/*'):
            os.unlink(f)
        os.unlink(flag)

    flag = get_ddh_disabled_ble_file_flag()
    if os.path.isfile(flag):
        _u(STATE_DDS_BLE_DISABLED)
        return False

    flag = get_ddh_app_override_file_flag()
    if os.path.isfile(flag):
        l_i_('[ BLE ] application override set')
        os.unlink(flag)
        return True

    l_h = ddh_get_json_app_type()
    speed_range = dds_get_json_moving_speed()

    # case: lobster trap, no speed requirement
    if not l_h:
        return True

    # case: trawling
    s_lo, s_hi = speed_range
    valid_moving_range = s_lo <= knots <= s_hi
    if l_h and valid_moving_range:
        return True

    _u('{}/{}'.format(STATE_DDS_BLE_APP_GPS_ERROR_SPEED, knots))


def _hci_is_up(i: int) -> bool:
    s = 'hciconfig -a hci{} | grep DOWN'.format(i)
    rv = sp.run(s, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return False if rv.returncode == 0 else True


def _hci_is_external(i: int) -> bool:
    # USB we use: EDUP brand, Realtek-based, ex. MAC: E8:4E:06:88:D1:8D
    # raspberry pi3 and pi4 has internal BLE == Manufacturer Cypress
    s = 'hciconfig -a hci{} | grep Cypress'.format(i)
    rv = sp.run(s, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode != 0


def ble_get_antenna_type():
    n = len(glob.glob('/sys/class/bluetooth/hci*'))

    # not raspberry
    if not linux_is_rpi():
        if n == 1:
            return 0, 'internal'
        if _hci_is_up(1):
            return 1, 'external'
        return 0, 'internal'

    # raspberry
    if n == 1:
        # we return whatever we have
        rv = 'external' if _hci_is_external(0) else 'internal'
        return 0, rv

    # more than one hci, prefer external one
    if _hci_is_external(0):
        if _hci_is_up(0):
            return 0, 'external'
        return 1, 'internal'

    if _hci_is_external(1):
        if _hci_is_up(1):
            return 1, 'external'
        return 0, 'internal'

    # fallback
    return 0, 'internal'


def ble_flag_dl():
    flag = get_dds_is_ble_downloading_flag()
    pathlib.Path(flag).touch()


def ble_un_flag_dl():
    flag = get_dds_is_ble_downloading_flag()
    if os.path.isfile(flag):
        os.unlink(flag)


def ble_un_flag_dl_at_boot():
    return ble_un_flag_dl()
