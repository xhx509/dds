import asyncio
import time
from mat.ddh_shared import send_ddh_udp_gui as _u
from dds.sns import sns_notify_ble_scan_exception
from dds.utils import print_ble_scan_banner
from mat.dds_states import *
from bleak import BleakScanner, BleakError
from dds.logs import lg_dds as lg


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

    except (Exception, ) as e:
        _u(STATE_DDS_BLE_HARDWARE_ERROR)
        lg.a('error: exception -> {}'.format(e))
        rv = 1
        return rv, {}


async def ble_scan(_lat, _lon, _dt, _h, _h_desc):
    """ scan, generic, just to find macs around """

    _u('{}/{}'.format(STATE_DDS_BLE_ANTENNA, _h_desc))
    rv, det = await _ble_scan(0)
    if rv:
        # todo > pass antenna to this exception
        sns_notify_ble_scan_exception(_lat, _lon)
        return {}
    return det


async def ble_scan_by_mac(mac, till=5, ad='hci0'):
    """ scan_by_mac, particular, generates device 'd' to connect """

    try:
        disc_result = await BleakScanner.discover(adapter=ad)
        macs_around = [i.address for i in disc_result]
        if mac not in macs_around:
            return
        _d = await BleakScanner.find_device_by_address(mac, timeout=till)
        return _d
    except (asyncio.TimeoutError, BleakError, OSError):
        lg.a('hardware error during scan')