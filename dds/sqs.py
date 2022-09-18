import datetime
import glob
import os
import time
import subprocess as sp
import json
import boto3
from dds.logs import lg_sqs as lg
from dds.sns import sns_serve
from mat.ddh_shared import dds_get_json_mac_dns, \
    get_dds_folder_path_sqs, \
    ddh_get_commit, \
    dds_get_commit, \
    dds_get_json_vessel_name
from mat.utils import linux_is_rpi3, linux_is_rpi4


# todo > maybe add a logger OK SQS message when download did OK


# -----------------
# SQS credentials
# -----------------
session = boto3.Session(
    aws_access_key_id=os.getenv('DDH_AWS_KEY_ID'),
    aws_secret_access_key=os.getenv('DDH_AWS_SECRET')
)
sqs = session.resource('sqs', region_name='us-east-2')
SQS_UP_QUEUE_NAME = os.getenv('DDH_SQS_UP_QUEUE_NAME')
SQS_PROJECT_NAME = os.getenv('DDH_AWS_PROJECT_NAME')


# ------------------
# SQS message types
# ------------------
SQS_BOOT = 'DDH_BOOT'
SQS_ERROR_BLE_HW = 'DDH_ERROR_BLE_HARDWARE'
SQS_LOGGER_DL = 'LOGGER_DOWNLOAD'
SQS_LOGGER_ERROR_OXYGEN = 'LOGGER_ERROR_OXYGEN'
SQS_LOGGER_MAX_ERRORS = 'LOGGER_ERRORS_MAXED_RETRIES'


def _msg_queue(q, m_body, m_attr=None):
    if not m_attr:
        m_attr = {}

    q.send_message(
        MessageBody=m_body,
        MessageAttributes=m_attr
    )


def _msg_dequeue(q, n=10, t=5):

    # n == max but if t is small, may get only 1
    msgs = q.receive_messages(
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=n,
        WaitTimeSeconds=t
    )
    s = '[ SQS ] asked de-queuing {} msgs, got {}'
    print(s.format(n, len(msgs)))
    return msgs


def sqs_ws():
    q = sqs.get_queue_by_name(QueueName=SQS_UP_QUEUE_NAME)
    msgs = _msg_dequeue(q)

    # forward as SNS
    for m in msgs:
        d = json.loads(m.body)
        i = m.message_id
        print('[ SQS_WS ] forwarding msg {} to SNS'.format(i))
        if sns_serve(d) == 0:
            # must be done by client after de-queuing
            m.delete()
        else:
            print('[ SQS_WS ] could not SNS msg {}'.format(i))


def _msg_build(description, lat, lon):
    t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    u = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rv_up = sp.run('uptime', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    plat = 'dev'
    if linux_is_rpi3():
        plat = 'rpi3'
    elif linux_is_rpi4():
        plat = 'rpi4'
    d = {
        'reason': description,
        'project': SQS_PROJECT_NAME,
        'vessel': dds_get_json_vessel_name(),
        'ddh_commit': ddh_get_commit(),
        'dds_commit': dds_get_commit(),
        'utc_time': str(u),
        'local_time': str(t),
        'box_sn': os.getenv('DDH_BOX_SERIAL_NUMBER'),
        'hw_uptime': rv_up.stdout.decode(),
        'gps_position': '{},{}'.format(lat, lon),
        'platform': plat
    }

    # save as file
    fol = str(get_dds_folder_path_sqs())
    now = int(time.time())
    path = '{}/{}.sqs'.format(fol, now)
    with open(path, 'w') as f:
        json.dump(d, f)

    # log it happened
    s = 'generated {} -> {} at {}, {}'
    lg.a(s.format(path, description, lat, lon))


def sqs_notify_ddh_booted(lat, lon):
    try:
        _msg_build(SQS_BOOT, lat, lon)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_ddh_booted: {}'.format(ex))


def sqs_notify_ble_scan_exception(lat, lon):
    try:
        _msg_build(SQS_ERROR_BLE_HW, lat, lon)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_ddh_error_ble_hardware: {}'.format(ex))


def _sqs_msg_logger_template(op, mac, lat, lon):
    try:
        lg_sn = dds_get_json_mac_dns(mac)
        s = '{}/{}/{}'.format(op, lg_sn, mac)
        _msg_build(s, lat, lon)
    except (Exception, ) as ex:
        lg.a('error sqs_msg_logger_template: {}'.format(ex))


def sqs_notify_logger_max_errors(mac, lat, lon):
    op = SQS_LOGGER_MAX_ERRORS
    return _sqs_msg_logger_template(op, mac, lat, lon)


def sqs_notify_oxygen_zeros(mac, lat, lon):
    op = SQS_LOGGER_ERROR_OXYGEN
    return _sqs_msg_logger_template(op, mac, lat, lon)


def sqs_notify_logger_download(mac, lat, lon):
    op = SQS_LOGGER_DL
    return _sqs_msg_logger_template(op, mac, lat, lon)


def sqs_serve():
    q = sqs.get_queue_by_name(QueueName=SQS_UP_QUEUE_NAME)
    fol = get_dds_folder_path_sqs()
    files = glob.glob('{}/*.sqs'.format(fol))
    for _ in files:
        f = open(_, 'r')
        d = json.load(f)
        try:
            lg.a('serving file {}'.format(_))
            _msg_queue(q, json.dumps(d))
            # delete SQS file
            os.unlink(_)
        except (Exception, ) as ex:
            lg.a('error sqs_serve: {}'.format(ex))
        finally:
            if f:
                f.close()


if __name__ == '__main__':
    sqs_notify_ddh_booted('my_lat', 'my_lon')
    sqs_serve()
    sqs_ws()
