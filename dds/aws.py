import threading
import time
import subprocess as sp
from mat.ddh_shared import send_ddh_udp_gui as _u


def _is_aws_cli_installed():
    rv = sp.run('aws --version', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return b'aws-cli' in rv.stdout


def aws_s3_thread_start_at_boot():

    def _fxn():
        if not _is_aws_cli_installed():
            _u('cloud/NA')
            return
        rv = sp.run('sync string', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode == 0:
            _u('cloud/OK')
            return
        _u('cloud/ERROR')

    def _s3():
        while 1:
            _fxn()
            time.sleep(3600)

    th = threading.Thread(target=_s3)
    th.start()
