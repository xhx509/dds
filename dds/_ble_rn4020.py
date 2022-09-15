import asyncio
import time
from bleak import BleakScanner, BleakClient, BleakError
from datetime import datetime, timezone, timedelta
from mat.ddh_shared import send_ddh_udp_gui as _u
from dds.ble_scan import ble_scan_by_mac
from dds.logs import lg_dds as lg
from dds.utils import crc_local_vs_remote, ble_progress_dl, build_cmd
from mat.dds_states import STATE_DDS_REQUEST_PLOT
from mat.logger_controller import SET_TIME_CMD, DEL_FILE_CMD, SWS_CMD, RWS_CMD
from mat.logger_controller_ble import DWG_FILE_CMD, CRC_CMD, GET_FILE_CMD
from mat.utils import dir_ans_to_dict
from settings.ctx import BLEAppException


UUID_RW = '00035b03-58e6-07dd-021a-08123a000301'


def _rae(rv, s):
    """ raises Ble App Exception """
    if rv:
        raise BLEAppException('rn4020 interact ' + s)


class _BleRN4020:
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
        for i in c:
            await self.cli.write_gatt_char(UUID_RW, i.encode())

    async def _ans_wait(self, timeout=1.0):
        while (not self._cmd_done) and \
                (self.cli and self.cli.is_connected) and \
                (timeout > 0):
            # accumulate in notification handler
            await asyncio.sleep(0.1)
            timeout -= 0.1
        print('>', self.ans)
        return self.ans

    async def connect(self, mac):
        def cb_disc(_: BleakClient):
            lg.a("disconnected OK")

        def c_rx(_: int, b: bytearray):
            self.ans += b

        # todo > see this makes sense
        if self.cli and self.cli.is_connected:
            await self.cli.disconnect()

        _d = await ble_scan_by_mac(mac)
        try:
            if _d:
                lg.a('connecting {}'.format(mac))
                self.cli = BleakClient(_d, disconnected_callback=cb_disc)
                if await self.cli.connect():
                    self.cli._mtu_size = 100
                    lg.a('mtu {}'.format(self.cli.mtu_size))
                    await self.cli.start_notify(UUID_RW, c_rx)
                    return 0
        except (asyncio.TimeoutError, BleakError, OSError) as er:
            print(er)
            pass
        return 1

    async def cmd_stp(self):
        await self._cmd('STP \r')
        rv = await self._ans_wait()
        return 0 if rv == b'\n\rSTP 0200\r\n' else 1

    async def cmd_gfv(self):
        await self._cmd('GFV \r')
        rv = await self._ans_wait()
        # rv: b'\n\rGFV 061.8.68\r\n'
        ok = len(rv) == 16 and b'GFV' in rv
        return 0 if ok else 1

    async def cmd_gtm(self):
        await self._cmd('GTM \r')
        rv = await self._ans_wait()
        ok = len(rv) == 29 and b'GTM' in rv
        return 0 if ok else 1

    async def cmd_get(self, s):
        c, _ = build_cmd(GET_FILE_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait(timeout=5)
        return 0 if b'\n\rGET 00\r\n' in rv else 1

    async def cmd_stm(self):
        # time() -> seconds since epoch, in UTC
        dt = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        c, _ = build_cmd(SET_TIME_CMD, dt.strftime('%Y/%m/%d %H:%M:%S'))
        await self._cmd(c)
        rv = await self._ans_wait()
        return 0 if rv == b'\n\rSTM 00\r\n' else 1

    async def cmd_del(self, s):
        c, _ = build_cmd(DEL_FILE_CMD, s)
        await self._cmd(c)
        rv = await self._ans_wait(timeout=10)
        return 0 if rv == b'\n\rDEL 00\r\n' else 1

    async def cmd_dir(self) -> tuple:
        # seems to need some time
        await asyncio.sleep(.5)
        await self._cmd('DIR \r')
        rv = await self._ans_wait()
        if not rv:
            return 1, 'not'
        if b'ERR' in rv:
            return 2, 'error'
        if rv and not rv.endswith(b'\x04\n\r'):
            return 3, 'partial'
        ls = dir_ans_to_dict(rv, '*', match=True)
        for s, z in ls.items():
            lg.a('DIR file {} size {}'.format(s, z))
        return 0, ls

    async def cmd_xmodem(self, z):
        # never used, dynamically resolves to a method
        # in superclass BleRN4020 w/o leading '_' character
        lg.a('error: this SHOULD never get called')
        return 0, bytes()

    async def cmd_sts(self):
        await self._cmd('STS \r')
        rv = await self._ans_wait()
        # rv: b'\n\rSTS 0201\r\n'
        ok = len(rv) == 12 and b'STS' in rv
        return 0 if ok else 1

    async def download_recipe(self, mac, g=None):

        rv = await self.connect(mac)
        _rae(rv, 'connecting')

        # todo > check RN4020 has no SWS
        rv = await self.cmd_stp()
        _rae(rv, 'stp')

        # rv = await self.cmd_gfv()
        # _rae(rv, 'gfv')
        # rv = await self.cmd_gtm()
        # _rae(rv, 'gtm')
        # rv = await self.cmd_stm()
        # _rae(rv, 'stm')

        # todo > need to do the BTC thing

        rv, ls = await self.cmd_dir()
        _rae(rv, 'dir error ' + str(rv))

        rv = await self.cmd_sts()
        _rae(rv, 'sts')

        # iterate files present in logger
        any_dl = False
        for name, size in ls.items():

            # skip non-interesting files
            if name.endswith('.cfg'):
                continue
            if name.startswith('Archive'):
                continue

            # download file
            rv = await self.cmd_get(name)
            _rae(rv, 'get')

            # dynamically resolved to method in class BleRN4020
            start = time.perf_counter()
            rv, data = await self.cmd_xmodem(size)
            _rae(rv, 'xmodem')
            speed = size / (time.perf_counter() - start)
            s = 'downloaded file {} OK, speed {} KBps'
            lg.a(s.format(name, speed / 1000))

            # save file in our local disk
            # path = str(get_dl_folder_path_from_mac(mac) / name)
            # create_folder_logger_by_mac(mac)
            # with open(path, 'wb') as f:
            #     f.write(file_data)

            # delete file in logger
            # rv = await self.cmd_del('18060DB_MATP_1Hz_(2).lid')
            # _rae(rv, 'del')
            # lg.a('file {} deleted in logger OK'.format(name))
            # any_dl = True

        # if g:
        #     rv = await self.cmd_rws(g)
        #     _rae(rv, 'rws')

        lg.a('logger {} download OK'.format(mac))

        if self.cli and self.cli.is_connected:
            await self.cli.disconnect()

        # plots
        # if not any_dl:
        #     return

        # plotting request to DDH
        _u('{}/{}'.format(STATE_DDS_REQUEST_PLOT, mac))
