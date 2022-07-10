#!/usr/bin/env python3


from services.dds_cnv_service import cnv_thread_start_at_boot
from dds.logs import *
from services.utils import check_dds_services

if __name__ == '__main__':

    # todo > set raspberry pi to do NTP we removed this code

    # debug
    #
    # os._exit(1)

    # log_core_start_at_boot()
    # log_tracking_start_at_boot()
    # macs_color_create_folder()
    # macs_color_show_at_boot()
    # ddh_check_conf_json_file()
    # linux_app_write_pid('dds')
    # _u('state_app_boot/')
    # gps_connect_shield()
    # gps_wait_for_it_at_boot()
    # lat, lon, dt_gps, speed = gps_measure()
    # gps_clock_sync_if_bad(dt_gps)

    check_dds_services()

    while 1:
        # gps_tell_vessel_name()
        # lat, lon, dt_gps, speed = gps_measure()
        # gps_clock_sync_if_bad(dt_gps)
        # if op_conditions_met(speed):
        #     h, d = ble_get_antenna_type()
        #     args = (lat, lon, h, d)
        #     ble_loop(*args)
        # log_tracking_update(lat, lon)

        # debug
        # ble_loop('11.11', '-22.22', 0, 'internal')


        # REQUIRED
        time.sleep(3)
