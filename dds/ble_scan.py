import asyncio
import time

from dds.sqs import sqs_notify_ble_scan_exception
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import *
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from dds.logs import lg_dds as lg


_g_ts_ble_hw_error = 0
PERIOD_BLE_TELL_HW_ERR_SECS = 600


def _ble_is_supported_logger(s):
    logger_types = ['DO-2', 'DO-1', 'DO-X',
                    'MOANA', 'MAT-2W', 'MATP-2W']
    for t in logger_types:
        if t in s:
            return True


async def ble_scan(_lat, _lon, _dt, _h, _h_desc, t=5.0):
    """ scan, generic, just to find macs around """

    def _scan_cb(d: BLEDevice, _):
        if _ble_is_supported_logger(d.name):
            _dd[d.address.lower()] = d.name

    # todo: do hci thing, adapter keyword, may need newer version, see BleakScanner class
    _dd = {}
    _u('{}/{}'.format(STATE_DDS_BLE_ANTENNA, _h_desc))

    try:
        scanner = BleakScanner(_scan_cb, None)
        await scanner.start()
        await asyncio.sleep(t)
        await scanner.stop()
        # print('_dd ---->', _dd)
        return _dd

    except (asyncio.TimeoutError, BleakError, OSError) as ex:
        global _g_ts_ble_hw_error
        now = time.perf_counter()
        if now > _g_ts_ble_hw_error:
            lg.a('hardware error during scan: {}'.format(ex))
            _g_ts_ble_hw_error = now + PERIOD_BLE_TELL_HW_ERR_SECS
            # todo > pass antenna to this
            sqs_notify_ble_scan_exception(_lat, _lon)
        return {}


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

    except (asyncio.TimeoutError, BleakError, OSError) as ex:
        lg.a('hardware error during scan: {}'.format(ex))
