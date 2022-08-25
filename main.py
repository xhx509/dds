#!/usr/bin/env python3


from dds.gps import gps_wait_for_it_at_boot, \
    gps_measure, gps_connect_shield, gps_clock_sync_if_so, \
    gps_tell_vessel_name
from dds.utils_ble_logs import *
from dds.sns import sns_serve, sns_notify_ddh_booted
from dds.utils_ble import ble_loop, ble_debug_hooks_at_boot
from mat.dds_states import STATE_DDS_BLE_APP_BOOT
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    ddh_check_conf_json_file, \
    ddh_get_macs_from_json_file, PID_FILE_DDS
from services.dds_aws_service import start_dds_aws_s3_service, is_dds_aws_s3_service_alive
from services.dds_cnv_service import start_dds_cnv_service, is_dds_cnv_service_alive
from settings.ctx import macs_color_create_folder, \
    macs_color_show_at_boot, \
    op_conditions_met, ble_get_antenna_type, \
    ble_flag_dl, ble_un_flag_dl, sns_create_folder, ble_un_flag_dl_at_boot


if __name__ == '__main__':

    ensure_we_run_only_one_instance('dds_core')

    start_dds_aws_s3_service()
    start_dds_cnv_service()

    ble_un_flag_dl_at_boot()
    log_core_start_at_boot()
    log_tracking_start_at_boot()
    macs_color_create_folder()
    sns_create_folder()
    macs_color_show_at_boot()
    ble_debug_hooks_at_boot()
    ddh_check_conf_json_file()
    linux_app_write_pid(PID_FILE_DDS)
    _u(STATE_DDS_BLE_APP_BOOT)

    gps_connect_shield()
    gps_wait_for_it_at_boot()
    lat, lon, tg, speed = gps_measure()
    gps_clock_sync_if_so(tg)
    sns_notify_ddh_booted(lat, lon)

    m_j = ddh_get_macs_from_json_file()

    while 1:
        is_dds_aws_s3_service_alive()
        is_dds_cnv_service_alive()

        gps_tell_vessel_name()
        g = gps_measure()
        if not g:
            time.sleep(1)
            continue

        lat, lon, tg, speed = g
        log_tracking_add(lat, lon)
        gps_clock_sync_if_so(tg)

        if op_conditions_met(speed):
            h, h_d = ble_get_antenna_type()
            args = (m_j, lat, lon, tg, h, h_d)
            ble_loop(*args)
        sns_serve()

        # required
        time.sleep(3)
