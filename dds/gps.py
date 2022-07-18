import datetime
import time
from dds.utils_ble_logs import l_d_, l_e_, l_i_
from mat.dds_states import STATE_DDS_BLE_APP_GPS_ERROR_POSITION, STATE_DDS_NOTIFY_BOAT_NAME, STATE_DDS_NOTIFY_GPS
from mat.gps import gps_configure_quectel, gps_get_rmc_data
from mat.utils import linux_is_rpi, linux_set_datetime
from settings import ctx as cu
from settings.ctx import hook_gps_dummy_measurement
from tzlocal import get_localzone
from mat.ddh_shared import send_ddh_udp_gui as _u, dds_get_json_vessel_name


def gps_connect_shield():

    if not cu.cell_shield_en:
        l_i_('[ BLE ] CELL shield set False, so no GPS')
        return

    if hook_gps_dummy_measurement:
        l_d_('[ BLE ] dummy GPS connected')
        return

    # after dummy
    if not linux_is_rpi():
        l_i_('[ BLE ] no GPS because not a raspberry')
        return

    for i in range(3):
        if gps_configure_quectel() == 0:
            return 0
        time.sleep(1)
        if i == 2:
            l_e_('[ BLE ] GPS, error opening port')
            return 1


def gps_measure(timeout=3):

    if cu.hook_gps_error_measurement_forced:
        _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)
        l_d_('[ GPS ] hook_gps_error_measurement_forced')
        return

    if cu.hook_gps_dummy_measurement or not linux_is_rpi():
        # l_d_('[ GPS ] hook_gps_dummy_measurement')
        time.sleep(.5)
        lat = '{:+.6f}'.format(38.000000000)
        lon = '{:+.6f}'.format(-83.0)
        return lat, lon, datetime.datetime.utcnow(), 1

    # real measure
    t = timeout
    g = gps_get_rmc_data(timeout=t)
    if g:
        lat = '{:+.6f}'.format(g[0])
        lon = '{:+.6f}'.format(g[1])
        if g[3] == '':
            g[3] = '0'
        # float, float, datetime UTC, string
        _u('{}/{},{}'.format(STATE_DDS_NOTIFY_GPS, lat, lon))
        return lat, lon, g[2], float(g[3])

    # failed
    _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)


def gps_clock_sync_if_so(dt_gps_utc):

    # todo: on RPi, test this GPS clock sync

    utc_now = datetime.datetime.utcnow()
    diff_secs = abs((dt_gps_utc - utc_now).total_seconds())
    if diff_secs < 60:
        return
    l_d_('[ GPS ] diff_secs = {}'.format(diff_secs))

    # use GPS time to sync local clock
    assert type(dt_gps_utc) is datetime.datetime
    z_my = get_localzone()
    z_utc = datetime.timezone.utc
    dt_my = dt_gps_utc.replace(tzinfo=z_utc).astimezone(tz=z_my)
    t = str(dt_my)[:-6]
    if not linux_is_rpi():
        l_e_('[ GPS ] not setting date on non-rpi')
        return
    return linux_set_datetime(t)


def gps_wait_for_it_at_boot():

    # Wikipedia: GPS-Time-To-First-Fix for cold start is typ.
    # 2 to 4 minutes, warm <= 45 secs, hot <= 22 secs

    till = time.perf_counter() + 300
    while time.perf_counter() < till:
        g = gps_measure()
        if g:
            # lat, lon, datetime UTC, speed
            return g
        time.sleep(1)

    return '', '', None, 0


g_last_time_told_vessel = time.perf_counter()


def gps_tell_vessel_name():
    global g_last_time_told_vessel
    now = time.perf_counter()
    if g_last_time_told_vessel + 10 < now:
        # too recent, leave
        return
    v = dds_get_json_vessel_name()
    _u('{}/{}'.format(STATE_DDS_NOTIFY_BOAT_NAME, v))
    g_last_time_told_vessel = time.perf_counter()



