from mat.ddh_shared import send_ddh_udp_gui as _u
from mat.ddh_shared import PID_FILE_DDS
import os
from mat.dds_states import STATE_DDS_NOTIFY_NET_VIA


def net_serve():

    if not os.path.exists(PID_FILE_DDS):
        v = 'inactive'
        _u('{}/{}'.format(STATE_DDS_NOTIFY_NET_VIA, v))
        return

    else:
        # the rest of states are emitted by the
        # dds_sw_net_service.py code
        pass
