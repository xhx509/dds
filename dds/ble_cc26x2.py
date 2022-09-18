import asyncio
import math
import os
import time
from bleak import BleakScanner, BleakClient, BleakError
from datetime import datetime, timezone, timedelta
from mat.ddh_shared import send_ddh_udp_gui as _u
from dds.ble_scan import ble_scan_target_mac
from dds.logs import lg_dds as lg
from dds.utils import crc_local_vs_remote, ble_progress_dl, build_cmd
from mat.ddh_shared import DDH_GUI_UDP_PORT, get_dl_folder_path_from_mac, \
    create_folder_logger_by_mac
from mat.dds_states import STATE_DDS_REQUEST_PLOT
from mat.logger_controller import SET_TIME_CMD, DEL_FILE_CMD, SWS_CMD, RWS_CMD
from mat.logger_controller_ble import DWG_FILE_CMD, CRC_CMD
from mat.utils import dir_ans_to_dict
from settings.ctx import BLEAppException
import humanize


# todo > see the MTU thing in BLEAK
# todo > move this file or part of it to mat library
# todo > remove all lg.a() from here

# new DO loggers
UUID_T = 'f000c0c2-0451-4000-b000-000000000000'
UUID_R = 'f000c0c1-0451-4000-b000-000000000000'

# old DO loggers
# UUID_T = 'f0001132-0451-4000-b000-000000000000'
# UUID_R = 'f0001131-0451-4000-b000-000000000000'


def _rae(rv, s):
    """ raises Ble App Exception """
    if rv:
        raise BLEAppException('cc26x2 interact ' + s)


class BleCC26X2:
    def __init__(self):
        self.cli = None
        self.ans = bytes()
        self.tag = ''
        self._cmd_done = False

    async def _cmd(self, c: str, empty=True):
        self.tag = c[:3]
        if empty:
            self.ans = bytes()
        print('<', c)
        await self.cli.write_gatt_char(UUID_R, c.encode())

    async def _ans_wait(self, timeout=1.0):
        while (not self._cmd_done) and \
                (self.cli and self.cli.is_connected) and \
                (timeout > 0):
            # accumulate in notification handler
            await asyncio.sleep(0.1)
            timeout -= 0.1
        if self.tag != 'DWL':
            print('>', self.ans)
        return self.ans

    async def cmd_stm(self):
        # time() -> seconds since epoch, in UTC
        dt = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        c, _ = build_cmd(SET_TIME_CMD, dt.strftime('%Y/%m/%d %H:%M:%S'))
        await self._cmd(c)
        rv = await self._ans_wait()
        return 0 if rv == b'STM 00' else 1

    async def cmd_dwg(self, s):
        c, _ = build_cmd(DWG_FILE_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait(timeout=10)
        return 0 if rv == b'DWG 00' else 1

    async def cmd_crc(self, s):
        c, _ = build_cmd(CRC_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait(timeout=10)
        ok = len(rv) == 14 and rv.startswith(b'CRC')
        if ok:
            return 0, rv[-8:].decode().lower()
        return 1, 'crc_error'

    async def cmd_del(self, s):
        c, _ = build_cmd(DEL_FILE_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait(timeout=10)
        return 0 if rv == b'DEL 00' else 1

    async def cmd_gtm(self):
        await self._cmd('GTM \r')
        rv = await self._ans_wait()
        ok = len(rv) == 25 and rv.startswith(b'GTM')
        return 0 if ok else 1

    async def cmd_stp(self):
        await self._cmd('STP \r')
        rv = await self._ans_wait()
        ok = rv in (b'STP 00', b'STP 0200')
        return 0 if ok else 1

    async def cmd_run(self):
        await self._cmd('RUN \r')
        rv = await self._ans_wait()
        ok = rv in (b'RUN 00', b'RUN 0200')
        return 0 if ok else 1

    async def cmd_mts(self):
        await self._cmd('MTS \r')
        rv = await self._ans_wait(timeout=20)
        return 0 if rv == b'MTS 00' else 1

    async def cmd_sws(self, g):
        # STOP with STRING
        lat, lon, _ = g
        lat = '{:+.6f}'.format(float(lat))
        lon = '{:+.6f}'.format(float(lon))
        s = '{} {}'.format(lat, lon)
        c, _ = build_cmd(SWS_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait()
        ok = rv in (b'SWS 00', b'SWS 0200')
        return 0 if ok else 1

    async def cmd_rws(self, g):
        # RUN with STRING
        lat, lon, _ = g
        lat = '{:+.6f}'.format(float(lat))
        lon = '{:+.6f}'.format(float(lon))
        s = '{} {}'.format(lat, lon)
        c, _ = build_cmd(RWS_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait()
        ok = rv in (b'RWS 00', b'RWS 0200')
        return 0 if ok else 1

    async def cmd_gfv(self):
        await self._cmd('GFV \r')
        rv = await self._ans_wait()
        ok = len(rv) == 12 and rv.startswith(b'GFV')
        return 0 if ok else 1

    async def cmd_utm(self):
        await self._cmd('UTM \r')
        rv = await self._ans_wait()
        ok = len(rv) == 14 and rv.startswith(b'UTM')
        if ok:
            _ = self.ans.split()[1].decode()
            b = _[-2:] + _[-4:-2] + _[-6:-4] + _[2:4]
            t = int(b, 16)
            s = humanize.naturaldelta(timedelta(seconds=t))
            print('utm', s)
            return 0, s
        return 1, ''

    async def cmd_dir(self) -> tuple:
        await self._cmd('DIR \r')
        rv = await self._ans_wait()
        if not rv:
            return 1, 'not'
        if rv == b'ERR':
            return 2, 'error'
        if rv and not rv.endswith(b'\x04\n\r'):
            return 3, 'partial'
        ls = dir_ans_to_dict(rv, '*', match=True)
        for s, z in ls.items():
            lg.a('DIR file {} size {}'.format(s, z))
        return 0, ls

    async def cmd_dwl(self, z, ip='127.0.0.1', port=DDH_GUI_UDP_PORT) -> tuple:

        # z: file size
        self.ans = bytes()
        n = math.ceil(z / 2048)
        ble_progress_dl(0, z, ip, port)
        ts = time.perf_counter()

        for i in range(n):
            c = 'DWL {:02x}{}\r'.format(len(str(i)), i)
            await self._cmd(c, empty=False)
            for j in range(30):
                await self._ans_wait(timeout=.1)
                if len(self.ans) == (i + 1) * 2048:
                    break
            ble_progress_dl(len(self.ans), z, ip, port)
            # print('chunk #{} len {}'.format(i, len(self.ans)))

        rv = 0 if z == len(self.ans) else 1
        if rv == 0:
            speed = z / (time.perf_counter() - ts)
            lg.a('speed {} KBps'.format(speed / 1000))
        return rv, self.ans

    async def disconnect(self):
        if self.cli and self.cli.is_connected:
            await self.cli.disconnect()

    async def connect(self, mac):
        def cb_disc(_: BleakClient):
            lg.a("disconnected OK")

        def c_rx(_: int, b: bytearray):
            self.ans += b

        _d = await ble_scan_target_mac(mac)
        try:
            if _d:
                lg.a('connecting {}'.format(mac))
                self.cli = BleakClient(_d, disconnected_callback=cb_disc)
                if await self.cli.connect():
                    # todo > check this MTU size matches firmware
                    self.cli._mtu_size = 244
                    lg.a('mtu {}'.format(self.cli.mtu_size))
                    await self.cli.start_notify(UUID_T, c_rx)
                    return 0
        except (asyncio.TimeoutError, BleakError, OSError):
            pass
        return 1

    async def download_recipe(self, mac, g=None):

        rv = await self.connect(mac)
        _rae(rv, 'connecting')

        if g:
            rv = await self.cmd_sws(g)
            _rae(rv, 'sws')
        else:
            rv = await self.cmd_stp()
            _rae(rv, 'stp')

        rv, t = await self.cmd_utm()
        _rae(rv, 'utm')

        rv = await self.cmd_gfv()
        _rae(rv, 'gfv')

        # rv = await self.cmd_mts()
        # _rae(rv, 'mts')

        rv = await self.cmd_gtm()
        _rae(rv, 'gtm')
        rv = await self.cmd_stm()
        _rae(rv, 'stm')

        rv, ls = await self.cmd_dir()
        _rae(rv, 'dir error ' + str(rv))

        # iterate files present in logger
        any_dl = False
        for name, size in ls.items():

            # skip MAT.cfg
            if name.endswith('.cfg'):
                continue

            # download file
            rv = await self.cmd_dwg(name)
            _rae(rv, 'dwg')
            rv, d = await self.cmd_dwl(int(size))
            _rae(rv, 'dwl')
            lg.a('downloaded file {} OK'.format(name))
            file_data = self.ans

            # calculate crc
            path = '/tmp/ddh_crc_file'
            with open(path, 'wb') as f:
                f.write(self.ans)
            rv, r_crc = await self.cmd_crc(name)
            _rae(rv, 'crc')
            rv, l_crc = crc_local_vs_remote(path, r_crc)
            s = 'file {} local CRC {} remote CRC {}'
            lg.a(s.format(name, l_crc, r_crc))
            if (not rv) and os.path.exists(path):
                lg.a('removing local file {} w/ bad CRC'.format(path))
                os.unlink(path)

            # save file in our local disk
            path = str(get_dl_folder_path_from_mac(mac) / name)
            create_folder_logger_by_mac(mac)
            with open(path, 'wb') as f:
                f.write(file_data)

            # delete file in logger
            rv = await self.cmd_del(name)
            _rae(rv, 'del')
            lg.a('file {} deleted in logger OK'.format(name))
            any_dl = True

        if g:
            rv = await self.cmd_rws(g)
            _rae(rv, 'rws')

        lg.a('logger {} download OK'.format(mac))

        if self.cli and self.cli.is_connected:
            await self.cli.disconnect()

        # plots
        if not any_dl:
            return

        # plotting request to DDH
        _u('{}/{}'.format(STATE_DDS_REQUEST_PLOT, mac))


async def ble_interact_cc26x2(mac, info, g):
    s = 'interacting with CC26X2 logger, info {}'
    lg.a(s.format(info))
    lc = BleCC26X2()

    try:
        await lc.download_recipe(mac, g)
        return 0

    except (Exception) as ex:
        print('--- exception', ex)
        # todo > to this disconnect for moana and rn4020
        await lc.disconnect()
        return 1


# test
def main():
    m = '60:77:71:22:CA:6D'
    i = 'DO-X'
    g = ('+1.111111', '-2.222222', datetime.now())
    try:
        asyncio.run(ble_interact_cc26x2(m, i, g))
    except Exception as ex:
        print('exception caught', ex)


if __name__ == '__main__':
    main()
