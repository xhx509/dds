#!/usr/bin/env python3


import os
import time
from services.dds_logs import DDSLogs
from dds.utils_ble_logs import l_e_
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    get_dds_folder_path_dl_files, \
    get_dds_aws_has_something_to_do_flag
import subprocess as sp
import datetime
from mat.dds_states import STATE_DDS_NOTIFY_CLOUD
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance, linux_is_rpi
from multiprocessing import Process
from settings import ctx


lg = DDSLogs('aws')


def _p(s):
    if type(s) is bytes:
        s = s.decode()
    lg.a(s)
    print(s)


def _get_aws_bin_path():
    if linux_is_rpi():
        return '/home/pi/li/venv/bin/aws'
    return 'aws'


def _s3():

    fol = get_dds_folder_path_dl_files()
    _k = os.getenv('DDH_AWS_KEY_ID')
    _s = os.getenv('DDH_AWS_SECRET')
    _n = os.getenv('DDH_AWS_NAME')
    _bin = _get_aws_bin_path()

    if _k is None or _s is None or _n is None:
        _p('missing credentials')
        _u('{}/log-in'.format(STATE_DDS_NOTIFY_CLOUD))
        return 1
    _n = 'bkt-' + _n

    c = 'AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} ' \
        '{} s3 sync {} s3://{} --dryrun'
    c = c.format(_k, _s, _bin, fol, _n)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    _t = datetime.datetime.now()
    if rv.returncode == 0:
        _u('{}/OK'.format(STATE_DDS_NOTIFY_CLOUD))
        _p('good cloud sync on {}'.format(_t))
        _p(rv.stdout)
        return 0

    _u('{}/ERR'.format(STATE_DDS_NOTIFY_CLOUD))
    _p('ERR cloud sync on {}'.format(_t))
    _p(rv.stderr)
    return 2


def _start_dds_aws_s3_service():

    ensure_we_run_only_one_instance('dds_aws')
    linux_app_write_pid('dds_aws')

    f = str(get_dds_aws_has_something_to_do_flag())

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('log created on {}'.format(now))

    while 1:
        if os.path.isfile(f):
            os.unlink(f)
            _p('[ AWS ] flag ddh_aws_has_something_to_do cleared')
            _s3()
            time.sleep(60)
            continue

        rv = _s3()
        if rv == 0:
            time.sleep(150)
        else:
            time.sleep(60)


def start_dds_aws_s3_service():
    p = Process(target=_start_dds_aws_s3_service)
    p.start()
    ctx.proc_aws = p


def is_dds_aws_s3_service_alive():
    if not ctx.proc_aws.is_alive():
        l_e_('[ AWS ] DDS AWS S3 service not alive')


# debug
if __name__ == '__main__':
    start_dds_aws_s3_service()
