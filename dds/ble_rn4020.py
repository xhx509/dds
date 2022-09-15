import asyncio
import datetime
import socket
import time

# todo > try a couple more days or fuck it do it with bluepy as always

from dds._ble_rn4020 import _BleRN4020, UUID_RW
from dds.logs import lg_dds as lg
from mat.ddh_shared import DDH_GUI_UDP_PORT
from mat.dds_states import STATE_DDS_BLE_DOWNLOAD_PROGRESS


# for GUI progress download
_sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
CAN = b'\x18'
NAK = b'\x15'


def _crc16(data):
    crc = 0x0000
    length = len(data)
    for i in range(0, length):
        crc ^= data[i] << 8
        for j in range(0,8):
            if (crc & 0x8000) > 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    v = crc & 0xFFFF
    return v.to_bytes(2, 'big')


def _xmd_frame_check_crc(b):
    rx_crc = b[-2:]
    data = b[3:-2]
    calc_crc = _crc16(data)
    # print(rx_crc, calc_crc)
    return calc_crc == rx_crc


def _utils_logger_is_rn4020(mac, info: str):
    a = '00:1E:C0'
    if mac.startswith(a) or mac.startswith(a.lower()):
        return True
    if 'MATP-2W' in info:
        return True


async def ble_interact_rn4020(mac, info, g):
    if not _utils_logger_is_rn4020(mac, info):
        s = 'not interacting w/ logger CC26X2, info {}'
        lg.a(s.format(info))
        return

    s = 'interacting with RN4020 logger, info {}'
    lg.a(s.format(info))
    lc = BleRN4020()
    if lc:
        await lc.download_recipe(mac, g)


g_verbose = False


def _debug(s):
    global g_verbose
    if g_verbose:
        print(s)


# extended with Xmodem
class BleRN4020(_BleRN4020):

    async def _ack(self):
        await self.cli.write_gatt_char(UUID_RW, b'\x06')

    async def _nak(self):
        await self.cli.write_gatt_char(UUID_RW, NAK)

    async def _can(self):
        await self.cli.write_gatt_char(UUID_RW, CAN)
        await self.cli.write_gatt_char(UUID_RW, CAN)
        await self.cli.write_gatt_char(UUID_RW, CAN)

    async def cmd_xmodem(self, z, ip='127.0.0.1', port=DDH_GUI_UDP_PORT):
        self.ans = bytes()
        file_built = bytes()
        _rt = 0
        _len = 0
        _eot = 0

        # GUI progress update
        _ = '{}/0'.format(STATE_DDS_BLE_DOWNLOAD_PROGRESS)
        _sk.sendto(str(_).encode(), (ip, port))

        # send 'C' character, special case
        _debug('<- C')
        await self.cli.write_gatt_char(UUID_RW, b'C')
        await asyncio.sleep(1)

        while 1:

            # rx last frame failure
            if len(self.ans) == 0:
                _debug('len self.ans == 0')
                return 1, bytes()

            # look first byte in, the control one
            b = self.ans[0:1]
            if b == EOT:
                # good, finished
                _debug('-> eot')
                await self._ack()
                _eot = 1
                break

            elif b == SOH:
                _debug('-> soh')
                _len = 128 + 5

            elif b == STX:
                _debug('-> stx')
                _len = 1024 + 5

            elif b == CAN:
                # bad, canceled by remote
                e = '-> can ctrl {}'.format(b)
                _debug(e)
                await self._ack()
                return 2, bytes()

            else:
                # bad, weird control byte arrived
                _debug('<- nak')
                await self._nak()
                await asyncio.sleep(5)
                return 3, bytes()

            # rx frame OK -> check CRC
            if _xmd_frame_check_crc(self.ans):
                file_built += self.ans[3:_len - 2]
                _rt = 0
                _debug('<- ack')
                await self._ack()

                # notify GUI progress update
                _ = len(file_built) / z * 100
                print('{}%'.format(int(_)))
                _ = '{}/{}'.format(STATE_DDS_BLE_DOWNLOAD_PROGRESS, _)
                _sk.sendto(str(_).encode(), (ip, port))

            else:
                # PARSE DATA not OK, check retries left
                _rt += 1
                if _rt == 5:
                    _debug('<- crc CAN')
                    await self._can()
                    return 4, bytes()
                _debug('<- crc NAK')
                await self._nak()

            # next rx frame attempt
            self.ans = bytes()
            for i in range(10):
                await asyncio.sleep(0.1)
                if len(self.ans) >= _len:
                    break

        # truncate to size instead of n * 1024
        if _eot == 1:
            file_built = file_built[0:z]

        _ = '{}/100'.format(STATE_DDS_BLE_DOWNLOAD_PROGRESS)
        _sk.sendto(str(_).encode(), (ip, port))
        return 0, file_built


# test
def main():
    m = '00:1E:C0:4D:BF:DB'
    i = 'MATP-2W'
    g = ('+1.111111', '-2.222222', datetime.datetime.now())
    try:
        asyncio.run(ble_interact_rn4020(m, i, g))
    except Exception as ex:
        print('exception caught', ex)


if __name__ == '__main__':
    main()
