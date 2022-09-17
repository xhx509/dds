import asyncio
from dds.hooks import hook_notify_ble_scan_exception
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import *
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from dds.logs import lg_dds as lg


def _ble_is_supported_logger(s):
    logger_types = ['DO-2', 'DO-1', 'DO-X',
                    'MOANA', 'MAT-2W', 'MATP-2W']
    for t in logger_types:
        if t in s:
            return True


async def _ble_scan(h, t=5.0) -> tuple:

    def _scan_cb(d: BLEDevice, _):
        if _ble_is_supported_logger(d.name):
            _dd[d.address.lower()] = d.name

    try:
        # todo: do hci thing, adapter keyword, may need newer version, see BleakScanner class
        _dd = {}
        scanner = BleakScanner(_scan_cb, None)
        await scanner.start()
        await asyncio.sleep(t)
        await scanner.stop()
        print('_dd ---->', _dd)
        return 0, _dd

    except (asyncio.TimeoutError, BleakError, OSError):
        lg.a('hardware error during scan')
        return 1, {}


async def ble_scan(_lat, _lon, _dt, _h, _h_desc):
    """ scan, generic, just to find macs around """

    _u('{}/{}'.format(STATE_DDS_BLE_ANTENNA, _h_desc))
    rv, det = await _ble_scan(0)
    if rv:
        # todo > pass antenna to this exception
        hook_notify_ble_scan_exception('sns', _lat, _lon)
        return {}
    return det


async def ble_scan_target_mac(mac, till=5, ad='hci0'):
    """ scan_by_mac, particular, generates device 'd' to connect """

    try:
        disc_result = await BleakScanner.discover(adapter=ad)

        # we try uppercase and lowercase :)
        macs_around = [i.address.lower() for i in disc_result]
        macs_around += [i.address.upper() for i in disc_result]
        if mac not in macs_around:
            return

        _d = await BleakScanner.find_device_by_address(mac, timeout=till)
        return _d

    except (asyncio.TimeoutError, BleakError, OSError):
        lg.a('hardware error during scan')
