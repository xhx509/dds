from dds.sns import *
from dds.sqs import *


# todo > do the SATELLITE ONES


def hook_notify_logger_error(via, mac, lat, lon):
    if via == 'sns':
        return sns_notify_logger_error(mac, lat, lon)
    elif via == 'sqs':
        return sqs_notify_logger_error(mac, lat, lon)
    # elif via == 'rdb':
    #     return rdb_notify_logger_error(mac, lat, lon)
    else:
        print('unknown hook notify via')


def hook_notify_ble_scan_exception(via, lat, lon):
    if via == 'sns':
        return sns_notify_ble_scan_exception(lat, lon)
    elif via == 'sqs':
        return sqs_notify_ble_scan_exception(lat, lon)
    # elif via == 'rdb':
    #     return rdb_notify_ble_scan_exception(lat, lon)
    else:
        print('unknown hook notify via')


def hook_notify_oxygen_zeros(via, mac, lat, lon):
    if via == 'sns':
        return sns_notify_oxygen_zeros(mac, lat, lon)
    if via == 'sqs':
        return sqs_notify_oxygen_zeros(mac, lat, lon)
    # if via == 'rdb':
    #     return rdb_notify_oxygen_zeros(mac, lat, lon)
    else:
        print('unknown hook notify via')


def hook_notify_ddh_booted(via, lat, lon):
    if via == 'sns':
        return sns_notify_ddh_booted(lat, lon)
    if via == 'sqs':
        return sqs_notify_ddh_booted(lat, lon)
    # if via == 'rdb':
    #     return rdb_notify_ddh_booted(lat, lon)
    else:
        print('unknown hook notify via')


def hook_notify_logger_download(via, mac, lat, lon):
    if via == 'sns':
        return sns_notify_logger_download(mac, lat, lon)
    if via == 'sqs':
        return sqs_notify_logger_download(mac, lat, lon)
    # if via == 'rdb':
    #     return rdb_notify_logger_download(mac, lat, lon)
    else:
        print('unknown hook notify via')
