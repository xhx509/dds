import asyncio
import time

from bleak import BleakScanner, BleakClient, BleakError
from datetime import datetime
from dds.logs import lg_dds as lg
from mat.ble.bluepy.cc26x2r_utils import utils_logger_is_cc26x2r_new
from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.dds_states import STATE_DDS_BLE_DOWNLOAD
from settings.ctx import BLEAppException


# todo > see the MTU thing in BLEAK

UUID_T = 'f000c0c2-0451-4000-b000-000000000000'
UUID_R = 'f000c0c1-0451-4000-b000-000000000000'


def _rae(rv, s):
    """ raises Ble App Exception """
    if rv:
        raise BLEAppException('cc26x2 interact ' + s)


async def _scan_by_mac(mac, t=5, ad='hci0'):
    try:
        s = 'scanning for {} seconds, adapter {}'
        print(s.format(t, ad))
        disc_result = await BleakScanner.discover(adapter=ad)
        for i in disc_result:
            print('\t', i.address, i.rssi, i.name)
        macs_around = [i.address for i in disc_result]
        if mac not in macs_around:
            return
        _d = await BleakScanner.find_device_by_address(mac, timeout=5)
        return _d
    except (asyncio.TimeoutError, BleakError, OSError):
        print('hw error')


class BleCC26X2:
    def __init__(self):
        self.cli = None
        self.ans = bytes()
        self.cmd = ''
        self._cmd_done = False

    async def _cmd(self, c: str):
        self.cmd = c
        print('<', c)
        await self.cli.write_gatt_char(UUID_R, c.encode())

    async def _ans_wait(self, timeout: int = 3):
        while (not self._cmd_done) and \
                (self.cli and self.cli.is_connected) and \
                (timeout > 0):
            # accumulate in notification handler
            await asyncio.sleep(0.1)
            timeout -= 0.1
        print(self.cmd, self.ans)
        return self.ans

    async def cmd_stm(self):
        await self._cmd('STM \r')
        return await self._ans_wait() == b'STM 00'

    async def cmd_gtm(self):
        await self._cmd('GTM \r')
        await self._ans_wait()

    async def connect(self, mac) -> bool:
        def cb_disc(_: BleakClient):
            print("disconnected OK")

        def c_rx(_: int, b: bytearray):
            self.ans += b

        _d = await _scan_by_mac(mac)
        try:
            if _d:
                print('connecting', mac)
                self.cli = BleakClient(_d, disconnected_callback=cb_disc)
                if await self.cli.connect():
                    await self.cli.start_notify(UUID_T, c_rx)
                    return True
        except (asyncio.TimeoutError, BleakError, OSError):
            pass
        return False

    async def download_recipe(self, mac):

        rv = await self.connect(mac)
        if not rv:
            print('failed connecting', mac)
        start_ts = datetime.now()

        _u(STATE_DDS_BLE_DOWNLOAD)

        # rv = await self.cmd_stm()
        # _rae(rv, 'stm')
        rv = await self.cmd_gtm()
        _rae(rv, 'gtm')

        # print('download OK')

        if self.cli and self.cli.is_connected:
            await self.cli.disconnect()


async def ble_interact_cc26x2(mac, info):
    if not utils_logger_is_cc26x2r_new(mac, info):
        return

    lg.a('interacting with CC26X2 logger')
    lc = BleCC26X2()
    await lc.download_recipe(mac)


# test
def main():
    m = '60:77:71:22:CA:6D'
    i = 'DO-X'
    asyncio.run(ble_interact_cc26x2(m, i))


if __name__ == '__main__':
    for i in range(1000):
        main()
        time.sleep(5)
