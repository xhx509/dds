import datetime
from pathlib import Path
from mat.ddh_shared import get_dds_folder_path_logs
from mat.utils import PrintColors as PC


class DDSLogs:
    @staticmethod
    def _gen_log_file_name() -> str:
        d = str(get_dds_folder_path_logs())
        Path(d).mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return '{}/{}.log'.format(d, now)

    def _retrieve_log_file_name(self):
        return self.f_name

    def __init__(self, label):
        self.label = label
        self.f_name = self._gen_log_file_name()

    def a(self, s):
        if type(s) is bytes:
            s = s.decode()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = '{} | [ {} ] {}'.format(now, self.label.upper(), s)
        with open(self.f_name, 'a') as f:
            f.write(s + '\n')

        if 'error' in s:
            PC.R(s)
        elif 'debug' in s:
            PC.B(s)
        elif 'warning' in s:
            PC.Y(s)
        else:
            PC.N(s)


lg_dds = DDSLogs('ble')
lg_aws = DDSLogs('aws')
lg_cnv = DDSLogs('cnv')
lg_sns = DDSLogs('sns')

