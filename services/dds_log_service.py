import datetime
import time

from mat.ddh_shared import get_dds_folder_path_logs
from pathlib import Path


class DDSLogs:
    @staticmethod
    def _gen_log_file_name(lbl) -> str:
        d = str(get_dds_folder_path_logs())
        Path(d).mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return '{}/{}_{}.log'.format(d, lbl, now)

    def __init__(self, label):
        self.label = label
        self.f_name = self._gen_log_file_name(label)

    def a(self, s):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = '{} [ {} ] {}'.format(now, self.label.upper(), s)
        with open(self.f_name, 'w+') as f:
            f.write(s + '\n')
        time.sleep(.01)


if __name__ == '__main__':
    lg = DDSLogs('my_log_Test')
    lg.a('iuhu')
