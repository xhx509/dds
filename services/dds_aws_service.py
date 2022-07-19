#!/usr/bin/env python3


import os
import time
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    get_dds_folder_path_dl_files, \
    get_dds_aws_has_something_to_do_flag
import subprocess as sp
import datetime
from mat.dds_states import STATE_DDS_NOTIFY_CLOUD
from mat.utils import linux_app_write_pid, ensure_we_run_only_one_instance
from dds_log_service import DDSLogs


lg = DDSLogs('aws')


def _p(s):
    if type(s) is bytes:
        s = s.decode()
    lg.a(s)
    print(s)


def _s3():

    fol = get_dds_folder_path_dl_files()
    _k = os.getenv('DDH_AWS_KEY_ID')
    _s = os.getenv('DDH_AWS_SECRET')
    _n = os.getenv('DDH_AWS_NAME')

    if _k is None or _s is None or _n is None:
        _p('missing credentials')
        _u('{}/log-in'.format(STATE_DDS_NOTIFY_CLOUD))
        return 1
    _n = 'bkt-' + _n

    c = 'AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} ' \
        'aws s3 sync {} s3://{} --dryrun'
    c = c.format(_k, _s, fol, _n)
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


def main():

    ensure_we_run_only_one_instance('dds-aws')
    linux_app_write_pid('dds-aws')

    f = str(get_dds_aws_has_something_to_do_flag())

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _p('log created on {}'.format(now))

    while 1:
        if os.path.isfile(f):
            _p('flag found')
            os.unlink(f)
            _s3()
            time.sleep(60)
            continue

        rv = _s3()
        if rv == 0:
            time.sleep(150)
        else:
            time.sleep(60)


# debug
if __name__ == '__main__':
    main()
