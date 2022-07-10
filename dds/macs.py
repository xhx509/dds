import glob
import os
import pathlib
import time
from dds.logs import l_i_
from mat.ddh_shared import get_dds_folder_path_macs


def _ble_get_color_macs(s) -> list:
    assert s in ('orange', 'black')
    valid = []
    now = int(time.time())
    fol = str(get_dds_folder_path_macs() / s)
    for f in glob.glob('{}/*'.format(fol)):
        mac, t = f.split('@')
        if float(t) > now:
            valid.append(mac)
        else:
            l_i_('[ MACS ] purge {}'.format(f))
            os.unlink(f)
    return valid


def macs_black():
    return _ble_get_color_macs('black')


def macs_orange():
    return _ble_get_color_macs('orange')


def _add_mac(c, m):
    assert c in ('orange', 'black')
    t = int(time.time())
    fol = str(get_dds_folder_path_macs() / c)
    m = '{}/{}@{}'.format(fol, m, t)
    pathlib.Path(m).touch()


def _rm_mac(c, m):
    assert c in ('orange', 'black')
    fol = str(get_dds_folder_path_macs() / c)
    wc = '{}/{}@*'.format(fol, m)
    for f in glob.glob(wc):
        l_i_('[ MACS ] delete {}'.format(f))
        os.unlink(f)


def add_mac_black(m): _add_mac('black', m)
def add_mac_orange(m): _add_mac('orange', m)
def rm_mac_black(m): _rm_mac('black', m)
def rm_mac_orange(m): _rm_mac('orange', m)


if __name__ == '__main__':
    add_mac_black('garsa')
    time.sleep(2)
    rm_mac_black('garsa')
