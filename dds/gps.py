import datetime
import time
import serial
from mat.dds_states import STATE_DDS_BLE_APP_GPS_ERROR_POSITION, \
    STATE_DDS_NOTIFY_BOAT_NAME, STATE_DDS_NOTIFY_GPS, \
    STATE_DDS_NOTIFY_GPS_BOOT
from mat.gps import PORT_CTRL, PORT_DATA
from mat.utils import linux_is_rpi, linux_set_datetime
from settings import ctx as cu
from settings.ctx import hook_gps_dummy_measurement
from tzlocal import get_localzone
from mat.ddh_shared import send_ddh_udp_gui as _u, dds_get_json_vessel_name
from dds.logs import lg_gps as lg


_g_ts_told_vessel = 0
_g_ts_cached_gps_valid_for = 0
_g_cached_gps = None
_g_ts_gga = 0


PERIOD_GPS_CACHE_VALID_SECS = 30
PERIOD_GPS_TELL_NUM_SATS_SECS = 300
PERIOD_GPS_TELL_VESSEL_SECS = 30
PERIOD_GPS_AT_BOOT_SECS = 300


def gps_get_cache():
    return _g_cached_gps


def _coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format

    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = '{}.{}'.format(head[-2:], x[1])
    decimal = int(deg) + float(minutes) / 60
    return decimal


def _gps_parse_rmc_frame(data: bytes):
    """ grab a long comma-separated string, parse fields """

    if b'GPRMC' not in data:
        return

    data = data.decode()
    s = '$GPRMC' + data.split('$GPRMC')[1].split('\r')[0]
    s = s.split(",")
    if s[2] == 'V':
        return

    _t = s[1][0:2] + ":" + s[1][2:4] + ":" + s[1][4:6]
    _day = s[9][0:2] + "/" + s[9][2:4] + "/" + s[9][4:6]

    # lat, direction, lon, direction, speed, course, variation
    lat = _coord_decode(s[3])
    dir_lat = s[4]
    lon = _coord_decode(s[5])
    dir_lon = s[6]
    speed = s[7]
    _course = s[8]
    # variation = s[10]

    # GPS date and time are UTC
    fmt = '{} {}'.format(_day, _t)
    gps_time = datetime.datetime.strptime(fmt, '%d/%m/%y %H:%M:%S')

    # display
    # print('time {} date {} lat {} lon {}'.format(_t, _day, lat, lon))
    # print('speed {} mag_var {} course {}'.format(speed, variation, _course))

    # return some strings
    lat = lat * 1 if dir_lat == 'N' else lat * -1
    lon = lon * 1 if dir_lon == 'E' else lon * -1

    # checksum skipping initial '$'
    cs_in = data.split('*')[1][:2]
    cs_calc = 0
    for c in data[1:].split('*')[0]:
        cs_calc ^= ord(c)
    cs_calc = '{:02x}'.format(int(cs_calc))
    if cs_in != cs_calc.upper():
        return None

    # everything went ok
    return lat, lon, gps_time, speed


def _gps_parse_gga_frame(data: bytes):
    """ grab a long comma-separated string, parse fields """

    if b'GPGGA' not in data:
        return

    # $GPGGA, time, lat, N, lon, W, 1, 07, 1.0, 9.0, M, , , , crc
    data = data.decode()

    # log satellites but not always
    global _g_ts_gga
    try:
        n = int(data[7])
        now = time.perf_counter()
        if now > _g_ts_gga:
            # todo > tell this to GUI
            lg.a('{} satellites in view'.format(n))
            _g_ts_gga = now + PERIOD_GPS_TELL_NUM_SATS_SECS

    except (Exception, ) as ex:
        lg.a('error: parse GGA frame {}'.format(ex))


def gps_connect_shield():

    if not cu.cell_shield_en:
        lg.a('CELL shield set False, so no GPS to configure')
        return

    if hook_gps_dummy_measurement:
        lg.a('debug: dummy GPS connected, not configuring it')
        return

    sp = serial.Serial(PORT_CTRL, baudrate=115200,
                       timeout=1, rtscts=True, dsrdtr=True)
    sp.write(b'AT+QGPS=1\r')
    ans = sp.readlines()
    rv = (b'+CME ERROR: 504\r\n' in ans) or b'OK\r\n' in ans
    lg.a('gps_connect_shield answer: {}'.format(ans))
    sp.close()
    time.sleep(0.5)
    return rv


def _gps_measure():
    """
    returns (lat, lon, dt object, speed) or None
    for a dummy or real GPS measurement
    """

    # hooks
    if cu.hook_gps_error_measurement_forced:
        _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)
        lg.a('debug: HOOK_GPS_ERROR_MEASUREMENT_FORCED')
        return

    if cu.hook_gps_dummy_measurement:
        lg.a('debug: HOOK_GPS_DUMMY_MEASUREMENT')
        time.sleep(.5)
        lat = '{:+.6f}'.format(38.000000000)
        lon = '{:+.6f}'.format(-83.0)
        return lat, lon, datetime.datetime.utcnow(), 1

    # real GPS measure
    sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.2, rtscts=True, dsrdtr=True)
    till = time.perf_counter() + 2
    sp.flushInput()

    # todo > see if these 2 hurt
    sp.readall()
    sp.flushInput()

    global _g_ts_cached_gps_valid_for
    global _g_cached_gps
    now = time.perf_counter()

    while 1:
        if time.perf_counter() > till:
            break

        b = sp.readall()
        # _gps_parse_gga_frame(b)
        g = _gps_parse_rmc_frame(b)
        if g:
            g = list(g)
            lat = '{:+.6f}'.format(g[0])
            lon = '{:+.6f}'.format(g[1])
            if g[3] == '':
                g[3] = '0'
            # float, float, datetime UTC, speed
            _u('{}/{},{}'.format(STATE_DDS_NOTIFY_GPS, lat, lon))
            _g_ts_cached_gps_valid_for = now + PERIOD_GPS_CACHE_VALID_SECS
            _g_cached_gps = lat, lon, g[2], float(g[3])
            return g

    if _g_ts_cached_gps_valid_for == 0:
        lg.a('failed, and no cache ever yet')
        return

    # failed, but we have GPS cache and is valid
    now = time.perf_counter()
    if now < _g_ts_cached_gps_valid_for:
        lat, lon, dt_utc, speed = _g_cached_gps
        _u('{}/{},{}'.format(STATE_DDS_NOTIFY_GPS, lat, lon))
        lg.a('using cached position {}, {}'.format(lat, lon))
        return _g_cached_gps

    lg.a('failed, and cache is too old')
    _g_cached_gps = '', '', None, float(0)

    # tell GUI
    _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)


def gps_measure():
    try:
        return _gps_measure()
    except (Exception, ) as ex:
        lg.a('error: {}'.format(ex))


def gps_clock_sync_if_so(dt_gps_utc):

    utc_now = datetime.datetime.utcnow()
    diff_secs = abs((dt_gps_utc - utc_now).total_seconds())
    if diff_secs < 60:
        return
    lg.a('debug: gps_cloc_sync_diff_secs = {}'.format(diff_secs))

    # use GPS time to sync local clock
    assert type(dt_gps_utc) is datetime.datetime
    z_my = get_localzone()
    z_utc = datetime.timezone.utc
    dt_my = dt_gps_utc.replace(tzinfo=z_utc).astimezone(tz=z_my)
    t = str(dt_my)[:-6]
    if not linux_is_rpi():
        # will not set date on non-rpi platforms
        return
    return linux_set_datetime(t)


def gps_wait_for_it_at_boot():

    # Wikipedia: GPS-Time-To-First-Fix for cold start is typ.
    # 2 to 4 minutes, warm <= 45 secs, hot <= 22 secs

    till = time.perf_counter() + PERIOD_GPS_AT_BOOT_SECS
    s = 'wait up to {} seconds for GPS at boot'
    lg.a(s.format(PERIOD_GPS_AT_BOOT_SECS))

    while 1:
        t = time.perf_counter()
        if t > till:
            return '', '', None, 0

        # todo > do this state at GUI
        t = int(till - time.perf_counter())
        _u('{}/{}'.format(STATE_DDS_NOTIFY_GPS_BOOT, t))

        g = gps_measure()
        if g:
            return g
        lg.a('gps_wait_at_boot returned {}'.format(g))
        s = '{} seconds left to wait for GPS at boot'
        lg.a(s.format(t))
        time.sleep(1)


def gps_tell_vessel_name():
    global _g_ts_told_vessel
    now = time.perf_counter()
    if now < _g_ts_told_vessel:
        return
    _g_ts_told_vessel = now + PERIOD_GPS_TELL_VESSEL_SECS
    v = dds_get_json_vessel_name()
    _u('{}/{}'.format(STATE_DDS_NOTIFY_BOAT_NAME, v))


if __name__ == '__main__':
    gps_connect_shield()
    while 1:
        m = gps_measure()
        print(m)
