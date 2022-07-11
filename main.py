#!/usr/bin/env python3


from dds.gps import gps_wait_for_it_at_boot, gps_measure, gps_connect_shield, gps_clock_sync_if_bad, \
    gps_tell_vessel_name
from dds.logs import *
from dds.sns import sns_serve, sns_notify_ddh_booted
from dds.utils_ble import ble_loop
from mat.utils import linux_app_write_pid
from services.utils import check_dds_services
from mat.ddh_shared import send_ddh_udp_gui as _u, ddh_check_conf_json_file, ddh_get_macs_from_json_file
from settings.ctx import macs_color_create_folder, macs_color_show_at_boot, op_conditions_met, ble_get_antenna_type, \
    ble_flag_dl


def ble_unflag_dl():
    pass


if __name__ == '__main__':

    log_core_start_at_boot()
    log_tracking_start_at_boot()
    macs_color_create_folder()
    macs_color_show_at_boot()
    ddh_check_conf_json_file()
    linux_app_write_pid('dds-core')
    _u('state_app_boot/')

    # gps_connect_shield()
    # gps_wait_for_it_at_boot()
    # lat, lon, dt_gps, speed = gps_measure()
    # gps_clock_sync_if_bad(dt_gps)
    # check_dds_services()
    # sns_notify_ddh_booted(lat, lon)

    macs_mon = ddh_get_macs_from_json_file()

    while 1:
        gps_tell_vessel_name()
        lat, lon, dt_gps, speed = gps_measure()
        gps_clock_sync_if_bad(dt_gps)
        if op_conditions_met(speed):
            ble_flag_dl()
            h, h_d = ble_get_antenna_type()
            args = (macs_mon, lat, lon, dt_gps, h, h_d)
            ble_loop(*args)
        ble_unflag_dl()
        log_tracking_update(lat, lon)
        sns_serve()


        # REQUIRED
        time.sleep(3)
