#!/usr/bin/env python3


import os
import time
from mat.ddh_shared import send_ddh_udp_gui as _u, \
    get_dds_folder_path_dl_files, \
    get_dds_folder_path_logs
import subprocess as sp
import logging
import datetime


date_fmt = "%Y-%b-%d %H:%M:%S"
t = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
_f = str(get_dds_folder_path_logs() / 'aws' / '{}.log'.format(str(t)))
logging.basicConfig(filename=_f,
                    filemode='w',
                    datefmt=date_fmt,
                    format='%(asctime)s [ %(levelname)s ] %(message)s',
                    level=logging.INFO)
_li = logging.info
_le = logging.error


def _p(s):
    if type(s) is bytes:
        s = s.decode()
    s = 'AWS | ' + s
    _li(s)
    print(s)


def _e(s):
    s = 'AWS | ' + s
    _le(s)
    print(s)


def _s3_main():

    _p('log file is {}'.format(_f))
    fol = get_dds_folder_path_dl_files()
    _k = os.getenv('DDH_AWS_KEY_ID')
    _s = os.getenv('DDH_AWS_SECRET')
    _n = os.getenv('DDH_AWS_NAME')

    if _k is None or _s is None or _n is None:
        _p('missing credentials')
        _u('cloud/bad')
        return
    _n = 'bkt-' + _n

    c = 'AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} ' \
        'aws s3 sync {} s3://{} --dryrun'
    c = c.format(_k, _s, fol, _n)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    _t = datetime.datetime.now()
    if rv.returncode == 0:
        _u('cloud/OK')
        _p('good cloud sync on {}'.format(_t))
        _p(rv.stdout)
        return
    _u('cloud/ERR')
    _e('BAD cloud sync on {}'.format(_t))
    _e(rv.stderr)


if __name__ == '__main__':
    while 1:
        _s3_main()
        time.sleep(3600)
