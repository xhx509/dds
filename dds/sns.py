import datetime
import glob
import os
import pathlib
import time
import subprocess as sp
from botocore.exceptions import EndpointConnectionError, ClientError
from mat.aws.sns import get_aws_sns_client
import json
from mat.ddh_shared import dds_get_json_vessel_name, ddh_get_commit, \
    get_dds_folder_path_sns, dds_get_commit, get_ddh_sns_force_file_flag, ddh_get_json_mac_dns
from mat.utils import linux_is_rpi3, linux_is_rpi4
from settings import ctx
from dds.logs import lg_sns as lg


# todo > maybe add a logger OK SNS message


g_last_notify = time.perf_counter()
g_last_time_notify_hw_exception = time.perf_counter()


def _sns_serve_notify(topic_arn, short_s, long_s):
    _ = topic_arn.split(':')
    parsed_region = _[3]

    try:
        cli = get_aws_sns_client(my_region=parsed_region)
        response = cli.publish(
            TargetArn=topic_arn,
            Message=json.dumps({'default': short_s,
                                'sms': short_s,
                                'email': long_s}),
            Subject=short_s,
            MessageStructure='json'
        )
        # response format very complicated, only use:
        if int(response['ResponseMetadata']['HTTPStatusCode']) == 200:
            lg.a('message published OK -> {}'.format(short_s))
            return 0

    except (ClientError, EndpointConnectionError, Exception) as e:
        lg.a('error: exception {}'.format(e))
        return 1


def sns_serve():
    if not ctx.sns_en:
        lg.a('notifications not enabled')
        return 1

    # -----------------
    # ARN topic checks
    # -----------------
    topic_arn = os.getenv('DDH_AWS_SNS_TOPIC_ARN')
    if topic_arn is None:
        lg.a('error: missing topic ARN')
        return 2

    if ':' not in topic_arn:
        lg.a('error: topic ARN malformed')
        return 3

    # --------------------------------------------------
    # flag is set by SNS functions, cleared at the end
    # --------------------------------------------------
    flag = get_ddh_sns_force_file_flag()
    if not os.path.isfile(flag):
        return 4
    lg.a('debug: detected force flag {}'.format(flag))

    # --------------------------------
    # grab & send SNS notifications
    # --------------------------------
    rv_all_sns = 0
    fol = get_dds_folder_path_sns()
    files = glob.glob('{}/*.sns'.format(fol))
    for _ in files:
        with open(_, 'r') as f:
            d = json.load(f)
            s = '{} - {}'.format(d['reason'], d['vessel'])
        rv = _sns_serve_notify(topic_arn, s, json.dumps(d))
        rv_all_sns += 0

        # delete SNS file
        if rv == 0:
            lg.a('served {}'.format(_))
            os.unlink(_)

    if rv_all_sns == 0 and os.path.isfile(flag):
        lg.a('debug: cleared force flag {}'.format(flag))
        os.unlink(flag)


def _sns_w_request(reason, lat, lon):
    com_ddh = ddh_get_commit()
    com_dds = dds_get_commit()
    v = dds_get_json_vessel_name()
    t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    u = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    ddh_box_sn = os.getenv('DDH_BOX_SERIAL_NUMBER')
    rv_up = sp.run('uptime', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)

    plat = 'dev'
    if linux_is_rpi3():
        plat = 'rpi3'
    elif linux_is_rpi4():
        plat = 'rpi4'

    d = {
        'reason': reason,
        'vessel': v,
        'ddh_commit': com_ddh,
        'dds_commit': com_dds,
        'utc_time': str(u),
        'local_time': str(t),
        'box_sn': ddh_box_sn,
        'hw_uptime': rv_up.stdout.decode(),
        'gps_position': '{},{}'.format(lat, lon),
        'platform': plat
    }
    fol = str(get_dds_folder_path_sns())
    now = int(time.time())
    path = '{}/{}.sns'.format(fol, now)
    with open(path, 'w') as f:
        json.dump(d, f)

    flag = get_ddh_sns_force_file_flag()
    pathlib.Path(flag).touch()


def sns_notify_logger_error(mac, lat, lon):
    sn = ddh_get_json_mac_dns(mac)
    s = 'LOGGER_{}_({})_TOO_MANY_ERRORS'.format(sn, mac)
    _sns_w_request(s, lat, lon)


def sns_notify_ble_scan_exception(lat, lon):
    global g_last_time_notify_hw_exception
    now = time.perf_counter()
    if g_last_time_notify_hw_exception + 86400 > now:
        return
    g_last_time_notify_hw_exception += 86400
    _sns_w_request('BLE_HARDWARE_ERROR', lat, lon)


def sns_notify_oxygen_zeros(mac, lat, lon):
    sn = ddh_get_json_mac_dns(mac)
    s = 'LOGGER_{}_({})_OXYGEN_ERROR'.format(sn, mac)
    _sns_w_request(s, lat, lon)


def sns_notify_ddh_booted(lat, lon):
    _sns_w_request('DDH_BOOTED', lat, lon)


def sns_notify_logger_download(mac, lat, lon):
    sn = ddh_get_json_mac_dns(mac)
    s = 'LOGGER_{}_({})_DOWNLOAD'.format(sn, mac)
    _sns_w_request(s, lat, lon)
