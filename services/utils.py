from dds.logs import l_i_
from mat.systemd import systemd_is_this_service_active, systemd_is_this_service_enabled


def check_dds_services():
    for s in ('ddh_aws_service',
              'ddh_cnv_service',
              'ddh_ble_service'):
        rv = systemd_is_this_service_enabled(s)
        l_i_('[ BLE ] {} enabled = {}'.format(s, rv))
        rv = systemd_is_this_service_active(s)
        l_i_('[ BLE ] {} active = {}'.format(s, rv))
