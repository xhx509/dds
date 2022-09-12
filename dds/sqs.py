import datetime
import os
import time
import subprocess as sp
import json
import boto3
from dds.logs import lg_sqs as lg
from mat.ddh_shared import ddh_get_json_mac_dns


# todo > do SQS as SNS based on files after testing

WS_DDH_BOOTED = 'DDH_BOOTED'
WS_DDH_ERROR_BLE_HARDWARE = 'DDH_ERROR_BLE_HARDWARE'
WS_LOGGER_DOWNLOAD = 'LOGGER_DOWNLOAD'
WS_LOGGER_ERROR_OXYGEN = 'LOGGER_ERROR_OXYGEN'
WS_LOGGER_ERRORS_MAX = 'LOGGER_ERRORS_MAXED_RETRIES'
WS_DDH_PRESENT_SET_XP_TIME = 5
WS_QUEUE_IN_NAME = 'ddw_in'
g_last_sqs_notify_error_ble_hw = time.perf_counter()


session = boto3.Session(
    aws_access_key_id=os.getenv('DDH_AWS_KEY_ID'),
    aws_secret_access_key=os.getenv('DDH_AWS_SECRET')
)
sqs = session.resource('sqs', region_name='us-east-2')


def _sqs_get_queue(name):
    return sqs.get_queue_by_name(QueueName=name)


def _sqs_enqueue_msg(q, m_body, m_attr=None):
    if not m_attr:
        m_attr = {}

    q.send_message(
        MessageBody=m_body,
        MessageAttributes=m_attr
    )


def _sqs_dequeue_msg(q, n, t):

    msgs = q.receive_messages(
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=n,
        WaitTimeSeconds=t
    )
    for m in msgs:
        lg.a('rx msg {}: {}'.format(m.message_id, m.body))
    return msgs


def _sqs_del_msg_from_queue(m):
    """ clients must delete message after they receive them """

    m.delete()
    lg.a('deleted message {}'.format(m.message_id))


def _sqs_build_json_msg(reason, lat, lon) -> str:

    com_ddh = 'v.1234'
    com_dds = 'v.4567'
    p = 'osu'
    v = 'boat_test'
    t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    u = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    ddh_box_sn = 'sn1234567'
    rv_up = sp.run('uptime', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    d = {
        'reason': reason,
        'project': p,
        'vessel': v,
        'ddh_commit': com_ddh,
        'dds_commit': com_dds,
        'utc_time': str(u),
        'local_time': str(t),
        'box_sn': ddh_box_sn,
        'hw_uptime': rv_up.stdout.decode(),
        'gps_position': '{},{}'.format(lat, lon)
    }
    return json.dumps(d)


def sqs_notify_ddh_booted(lat, lon):
    try:
        q = _sqs_get_queue(WS_QUEUE_IN_NAME)
        m = _sqs_build_json_msg(WS_DDH_BOOTED, lat, lon)
        lg.a('<- DDS booted', lat, lon)
        _sqs_enqueue_msg(q, m)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_ddh_booted: {}'.format(ex))


def sqs_notify_ble_scan_exception(lat, lon):
    try:
        q = _sqs_get_queue(WS_QUEUE_IN_NAME)
        global g_last_sqs_notify_error_ble_hw
        now = time.perf_counter()
        if g_last_sqs_notify_error_ble_hw + 86400 > now:
            return
        g_last_sqs_notify_error_ble_hw += 86400
        lg.a('<- DDS BLE hardware error')
        m = _sqs_build_json_msg(WS_DDH_ERROR_BLE_HARDWARE, lat, lon)
        _sqs_enqueue_msg(q, m)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_ddh_error_ble_hardware: {}'.format(ex))


def _sqs_msg_logger_template(op, mac, lat, lon):
    try:
        lg_sn = ddh_get_json_mac_dns(mac)
        q = _sqs_get_queue(WS_QUEUE_IN_NAME)
        s = '{}/{}/{}'.format(op, lg_sn, mac)
        m = _sqs_build_json_msg(s, lat, lon)
        print('sqs {} <- {}'.format(op, s))
        return _sqs_enqueue_msg(q, m)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_logger_template: {}'.format(ex))


def sqs_notify_logger_error(mac, lat, lon):
    lg_sn = ddh_get_json_mac_dns(mac)
    op = WS_LOGGER_ERRORS_MAX
    return _sqs_msg_logger_template(op, mac, lg_sn, lat, lon)


def sqs_notify_oxygen_zeros(mac, lat, lon):
    lg_sn = ddh_get_json_mac_dns(mac)
    op = WS_LOGGER_ERROR_OXYGEN
    return _sqs_msg_logger_template(op, mac, lg_sn, lat, lon)


def sqs_notify_logger_download(mac, lat, lon):
    lg_sn = ddh_get_json_mac_dns(mac)
    op = WS_LOGGER_DOWNLOAD
    return _sqs_msg_logger_template(op, mac, lg_sn, lat, lon)


# testing
def main():
    print(os.getenv('DDH_AWS_KEY_ID'))
    sqs_notify_ddh_booted('my_lat', 'my_lon')


if __name__ == '__main__':
    main()
