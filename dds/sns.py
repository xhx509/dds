import datetime
import glob
import os
import pathlib
import time
import subprocess as sp
from botocore.exceptions import EndpointConnectionError, ClientError
from dds.logs import l_e_, l_i_, l_w_
from mat.aws.sns import get_aws_sns_client
import json
from mat.ddh_shared import dds_get_json_vessel_name, ddh_get_commit, \
    get_dds_folder_path_sns, dds_get_commit, get_ddh_sns_force_file_flag
from settings import ctx


g_last_notify = time.perf_counter()
g_last_time_notify_hw_exception = time.perf_counter()


def _sns_req():
    flag = get_ddh_sns_force_file_flag()
    pathlib.Path(flag).touch()


def _sns_notify(topic_arn, short_s, long_s):
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
            l_i_('[ SNS ] message published OK -> {}'.format(short_s))
            return 0

    except (ClientError, EndpointConnectionError, Exception) as e:
        l_e_('[ SNS ] exception {}'.format(e))
        return 1


def sns_serve():
    if not ctx.sns_en:
        l_i_('[ SNS ] not enabled')
        return

    flag = get_ddh_sns_force_file_flag()
    if not os.path.isfile(flag):
        return
    l_w_('[ SNS ] detected force flag')
    os.unlink(flag)

    # -----------------
    # ARN topic checks
    # -----------------
    topic_arn = os.getenv('DDH_AWS_SNS_TOPIC_ARN')
    if topic_arn is None:
        l_e_('[ SNS ] missing topic ARN')
        return 1

    if ':' not in topic_arn:
        l_e_('[ SNS ] topic ARN malformed')
        return 1

    # --------------------------------
    # grab and send SNS notifications
    # --------------------------------
    fol = get_dds_folder_path_sns()
    files = glob.glob('{}/*.sns'.format(fol))
    for _ in files:
        with open(_, 'r') as f:
            d = json.load(f)
            s = 'DDH {} - {}'
            s.format(d['reason'], d['vessel'])
        rv = _sns_notify(topic_arn, s, json.dumps(s))
        if rv == 0:
            l_i_('[ SNS ] served {}'.format(_))
            os.unlink(_)


def _sns_add(reason, lat, lon):
    com_ddh = ddh_get_commit()
    com_dds = dds_get_commit()
    v = dds_get_json_vessel_name()
    t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    u = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    ddh_box_sn = os.getenv('DDH_BOX_SERIAL_NUMBER')
    rv_up = sp.run('uptime', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    d = {
        'reason': reason,
        'vessel': v,
        'ddh_commit': com_ddh,
        'dds_commit': com_dds,
        'utc_time': str(u),
        'local_time': str(t),
        'box_sn': ddh_box_sn,
        'hw_uptime': rv_up.stdout.decode(),
        'gps_position': '{},{}'.format(lat, lon)
    }
    fol = str(get_dds_folder_path_sns())
    now = int(time.time())
    path = '{}/{}.sns'.format(fol, now)
    with open(path, 'w') as f:
        json.dump(d, f)


def sns_notify_logger_error(mac, lat, lon):
    s = 'LOGGER_{}_TOO_MANY_ERRORS'.format(mac)
    _sns_add(s, lat, lon)
    _sns_req()


def sns_notify_ble_scan_exception(lat, lon):
    global g_last_time_notify_hw_exception
    now = time.perf_counter()
    if g_last_time_notify_hw_exception + 86400 > now:
        return
    g_last_time_notify_hw_exception += 86400
    _sns_add('BLE_HARDWARE_MAY_BE_BAD', lat, lon)
    _sns_req()


def sns_notify_dissolved_oxygen_zeros(mac, lat, lon):
    s = 'LOGGER_{}_OXYGEN_ERROR'.format(mac)
    _sns_add(s, lat, lon)
    _sns_req()


def sns_notify_ddh_booted(lat, lon):
    _sns_add('DDH_BOOTED', lat, lon)
    _sns_req()
