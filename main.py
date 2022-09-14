#!/usr/bin/env python3
import asyncio
import time
from dds.aws import aws_serve
from dds.ble_scan import ble_scan
from dds.cnv import cnv_serve
from dds.gps import gps_wait_for_it_at_boot, \
    gps_measure, gps_connect_shield, gps_clock_sync_if_so, \
    gps_tell_vessel_name, gps_get_cache
from dds.net import net_serve
from dds.sns import sns_serve, sns_notify_ddh_booted
from dds.utils import dds_log_core_start_at_boot, dds_log_tracking_start_at_boot, dds_log_tracking_add
from dds.ble import ble_apply_debug_hooks_at_boot, ble_show_monitored_macs, ble_interact_w_logger
from mat.dds_states import STATE_DDS_BLE_APP_BOOT
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    dds_check_conf_json_file, \
    dds_get_macs_from_json_file, PID_FILE_DDS
from settings import ctx
from settings.ctx import dds_create_macs_color_folders, \
    macs_color_show_at_boot, \
    op_conditions_met, ble_get_antenna_type, \
    dds_create_sns_folder, dds_create_dl_files_folder, dds_create_logs_folder


if __name__ == '__main__':

    ensure_we_run_only_one_instance('dds_core')
    dds_create_macs_color_folders()
    dds_create_sns_folder()
    dds_create_dl_files_folder()
    dds_create_logs_folder()

    dds_log_core_start_at_boot()
    dds_log_tracking_start_at_boot()

    dds_check_conf_json_file()
    m_j = dds_get_macs_from_json_file()
    macs_color_show_at_boot()
    ble_show_monitored_macs()
    ble_apply_debug_hooks_at_boot()
    linux_app_write_pid(PID_FILE_DDS)
    _u(STATE_DDS_BLE_APP_BOOT)

    gps_connect_shield()
    gps_wait_for_it_at_boot()
    lat, lon, tg, speed = gps_measure()
    gps_clock_sync_if_so(tg)

    # hook_notify_ddh_booted('sns', lat, lon)

    while 1:
        gps_tell_vessel_name()
        g = gps_measure()
        if not g:
            # todo > test this
            g = gps_get_cache()
            if not g[0]:
                continue

        lat, lon, tg, speed = g
        dds_log_tracking_add(lat, lon)
        gps_clock_sync_if_so(tg)

        if op_conditions_met(speed):
            h, h_d = ble_get_antenna_type()

            # find BLE loggers around
            args = [lat, lon, tg, h, h_d]
            det = ctx.ael.run_until_complete(ble_scan(*args))

            # download detected loggers, if any
            args = [det, m_j, lat, lon, tg, h, h_d]
            ctx.ael.run_until_complete(ble_interact_w_logger(*args))

        cnv_serve()
        # sns_serve()
        # aws_serve()
        # sqs_serve()
        net_serve()
