import glob
import os
import pathlib
import time
from mat.ddh_shared import get_dds_folder_path_macs, \
    get_dds_loggers_forget_time
from dds.logs import lg_dds as lg


def _ble_get_color_macs(s) -> list:
    assert s in ('orange', 'black')
    valid = []
    now = int(time.time())
    fol = str(get_dds_folder_path_macs() / s)
    wc = '{}/*'.format(fol)

    for f in glob.glob(wc):
        mac, t = f.split('@')
        if now > int(t):
            lg.a('MACS purge {}'.format(f))
            os.unlink(f)
        else:
            valid.append(mac)
    return valid


def macs_black():
    return _ble_get_color_macs('black')


def macs_orange():
    return _ble_get_color_macs('orange')


def _add_mac(c, mac):
    assert c in ('orange', 'black')
    ft = get_dds_loggers_forget_time()
    if c == 'orange':
        ft = 30
    t = int(time.time()) + ft
    fol = str(get_dds_folder_path_macs() / c)
    mac = mac.replace(':', '-')
    f = '{}/{}@{}'.format(fol, mac, t)
    pathlib.Path(f).touch()
    s = 'BLE {}\'ed mac {}, value {}, now {}'
    now = int(time.time())
    lg.a(s.format(c, mac, t, now))


def _rm_mac(c, m):
    assert c in ('orange', 'black')
    m = m.replace(':', '-')
    fol = str(get_dds_folder_path_macs() / c)
    wc = '{}/{}@*'.format(fol, m)
    for f in glob.glob(wc):
        lg.a('MACS delete {}'.format(f))
        os.unlink(f)


def add_mac_black(m): _add_mac('black', m)
def add_mac_orange(m): _add_mac('orange', m)
def rm_mac_black(m): _rm_mac('black', m)
def rm_mac_orange(m): _rm_mac('orange', m)


def is_mac_in_black(m, b):
    # b: [<path>/black/60-77-71-22-c8-6f', ...]
    m = m.replace(':', '-')
    return m in str(b)


def is_mac_in_orange(m, o):
    m = m.replace(':', '-')
    return m in str(o)
