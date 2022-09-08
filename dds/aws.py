#!/usr/bin/env python3

import os
import time

from dds.logs import lg_aws as lg
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    get_dds_folder_path_dl_files
import subprocess as sp
import datetime
from mat.dds_states import STATE_DDS_NOTIFY_CLOUD
from mat.utils import linux_is_rpi
from settings import ctx


def _get_aws_bin_path():
    if linux_is_rpi():
        return '/home/pi/li/venv/bin/aws'
    return 'aws'


def aws_serve():
    now = time.perf_counter()
    if ctx.ts_last_aws == 0:
        lg.a('doing first upload ever')
    else:
        # todo > set this time as constant somewhere
        if ctx.ts_last_aws + 30 > now:
            return
        lg.a('lets see if we have stuff to upload')

    ctx.ts_last_aws = now

    fol = get_dds_folder_path_dl_files()
    _k = os.getenv('DDH_AWS_KEY_ID')
    _s = os.getenv('DDH_AWS_SECRET')
    _n = os.getenv('DDH_AWS_NAME')
    _bin = _get_aws_bin_path()

    _u('{}/busy'.format(STATE_DDS_NOTIFY_CLOUD))

    if _k is None or _s is None or _n is None:
        lg.a('missing credentials')
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
        lg.a('good cloud sync on {}'.format(_t))
        lg.a(rv.stdout)
        return 0

    _u('{}/ERR'.format(STATE_DDS_NOTIFY_CLOUD))
    lg.a('AWS error: cloud sync on {}'.format(_t))
    lg.a(rv.stderr)
    return 2

