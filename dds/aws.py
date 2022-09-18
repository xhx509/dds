#!/usr/bin/env python3

import os
import time
from dds.logs import lg_aws as lg
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    get_dds_folder_path_dl_files
import subprocess as sp
import datetime
from mat.dds_states import *
from mat.utils import linux_is_rpi
from settings import ctx


def _get_aws_bin_path():
    if linux_is_rpi():
        return '/home/pi/li/venv/bin/aws'
    return 'aws'


_g_ts_aws = 0
PERIOD_AWS_S3_SECS = 600


def aws_serve():

    global _g_ts_aws
    now = time.perf_counter()
    if now < _g_ts_aws:
        return
    if _g_ts_aws == 0:
        lg.a('doing first upload ever')

    _g_ts_aws = now + PERIOD_AWS_S3_SECS

    fol = get_dds_folder_path_dl_files()
    _k = os.getenv('DDH_AWS_KEY_ID')
    _s = os.getenv('DDH_AWS_SECRET')
    _n = os.getenv('DDH_AWS_NAME')
    _bin = _get_aws_bin_path()

    _u(STATE_DDS_NOTIFY_CLOUD_BUSY)

    if _k is None or _s is None or _n is None:
        lg.a('missing credentials')
        _u(STATE_DDS_NOTIFY_CLOUD_LOGIN)
        return 1
    _n = 'bkt-' + _n

    c = 'AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} ' \
        '{} s3 sync {} s3://{} --dryrun'
    c = c.format(_k, _s, _bin, fol, _n)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    _t = datetime.datetime.now()
    if rv.returncode == 0:
        _u(STATE_DDS_NOTIFY_CLOUD_OK)
        lg.a('good cloud sync on {}'.format(_t))
        lg.a(rv.stdout)
        return 0

    _u(STATE_DDS_NOTIFY_CLOUD_ERR)
    lg.a('AWS error: cloud sync on {}'.format(_t))
    lg.a(rv.stderr)
    return 2

