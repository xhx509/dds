import datetime
import os
import threading
import time
import subprocess as sp
from botocore.exceptions import EndpointConnectionError, ClientError

from dds.db.db_sns import DbSNS
from dds.logs import l_e_, l_i_
from mat.aws.sns import get_aws_sns_client
import json
from mat.ddh_shared import get_dds_settings_file, ddh_get_json_vessel_name, ddh_get_commit, get_ddh_db_sns
from settings import ctx


def _sns_notify(short_s, long_s):
    topic_arn = os.getenv('DDH_AWS_SNS_TOPIC_ARN')

    if topic_arn is None:
        l_e_('[ SNS ] missing topic ARN')
        return 1

    if ':' not in topic_arn:
        l_e_('[ SNS ] topic ARN malformed')
        return 1

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


def _sns_notify_ddh_alive(still=False):
    com = ddh_get_commit()
    v = ddh_get_json_vessel_name()
    t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    u = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    _ = 'BOOTED' if not still else 'STILL OPERATIONAL'
    ddh_box_sn = os.getenv('DDH_BOX_SERIAL_NUMBER')
    short_s = 'DDH v.{} - vessel {} - utc time {} -> {}'.format(com, v, u, _)
    rv = sp.run('uptime', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    long_s = 'DDH hardware serial number -> {}\n'.format(ddh_box_sn)
    long_s += 'DDH hardware uptime -> {}'.format(rv.stdout.decode())
    long_s += 'DDH local time -> {}\n'.format(t)
    # todo > do a semaphore controlled GPS measure here
    # lat = back['gps']['lat']
    # lon = back['gps']['lon']
    # long_s += 'DDH GPS position -> {},{}\n'.format(lat, lon)
    rv = _sns_notify(short_s, long_s)
    return rv


def sns_notify_logger_error(short_s, long_s):
    return _sns_notify(short_s, long_s)


def sns_notify_ble_scan_exception():
    v = ddh_get_json_vessel_name()
    short_s = 'DDH {} got several scan BLE exceptions'.format(v)
    long_s = 'Please check it'
    return _sns_notify(short_s, long_s)


def sns_notify_dissolved_oxygen_zeros(mac):
    v = ddh_get_json_vessel_name()
    short_s = 'DDH {} got oxygen as zeros for logger {}'.format(v, mac)
    long_s = 'Please check it'
    return _sns_notify(short_s, long_s)


def main():
    if not ctx.sns_en:
        l_i_('[ SNS ] not enabled at boot')
        return

    def _fxn_sns_logger_errors():
        db = DbSNS(get_ddh_db_sns())
        db.db_get()
        v = ddh_get_json_vessel_name()

        # -----------------------------------------
        # grab errors from SNS database
        # num, addr, timestamp, desc, flag served
        # -----------------------------------------
        for each in db.get_records_by_non_served():
            i, mac, t, desc, served = each
            s = 'DDH {} logger error mac {}'.format(v, mac)
            l_i_('[ SNS ] notifying {} -> {}'.format(s, desc))

            # ---------------------------------------
            # notify them via SNS, mark them as done
            # ---------------------------------------
            if sns_notify_logger_error(s, desc) == 0:
                db.mark_as_served(mac, t, desc)

    def _sns_logger_errors():
        _fxn_sns_logger_errors()
        time.sleep(3600)

    def _sns_ddh_alive():
        _sns_notify_ddh_alive(still=False)
        while 1:
            _sns_notify_ddh_alive(still=True)
            time.sleep(86400)

    _se = threading.Thread(target=_sns_logger_errors)
    _se.start()
    _sa = threading.Thread(target=_sns_ddh_alive)
    _sa.start()




