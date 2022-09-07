import asyncio
import logging
import traceback
from bleak import BleakScanner, BleakClient, BleakError
from datetime import datetime

# from ddh.threads.utils_core import core_set_state, STATE_BLE_DL_ONGOING


UUID_R = '569a2001-b87f-490c-92cb-11ba5ea5167c'
UUID_T = '569a2000-b87f-490c-92cb-11ba5ea5167c'


async def _scan_by_mac(mac, t=5, ad='hci0'):
    try:
        s = 'BLE scanning for {} seconds, adapter {}'
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
        print('BLE hw error')


class BleDO2:
    def __init__(self):
        self.cli = None
        self.ans = bytes()
        self.cmd = ''
        self._cmd_done = False

    async def _cmd(self, c: str):
        self.cmd = c
        print('<', c)
        await self.cli.write_gatt_char(UUID_R, c.encode())

    async def _ans_wait(self, timeout: int = 60):
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

    async def download_files(self, mac):

        rv = await self.connect(mac)
        if not rv:
            print('failed connecting', mac)
        start_ts = datetime.now()

        # update icons
        # core_set_state(STATE_BLE_DL_ONGOING)

        while self.cli and self.cli.is_connected:
            if (datetime.now() - start_ts).total_seconds() > 600:
                print('download timeout')
                break

            # rv = await self.cmd_stm()
            # if not rv:
            #     break
            # print('download OK')

        if self.cli and self.cli.is_connected:
            self.cli.disconnect()


if __name__ == '__main__':
    # scan_using_bluepy()
    try:
        _mac = '11:22:33:44:55:66'
        lc = BleDO2()
        asyncio.run(lc.download_files(_mac))

    except (Exception, ) as e:
        logging.error(traceback.format_exc())
