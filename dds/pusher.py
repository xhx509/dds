import subprocess as sp


CODE_DDH_BOOTED = 0
CODE_DDH_KEEP_ALIVE = 1
CODE_DDH_SUPPORT_REQUEST = 2
CODE_LOGGER_DOWNLOAD_OK = 3
CODE_LOGGER_DOWNLOAD_ERROR = 4
CODE_TEST = 9


# def _create_file_to_be_pushed(msg_code, logger_mac=''):
#     if msg_code in (
#             CODE_DDH_BOOTED,
#             CODE_DDH_KEEP_ALIVE,
#             CODE_DDH_SUPPORT_REQUEST):
#         assert logger_mac == ''
#
#     ddh_sn = os.getenv('DDH_BOX_SERIAL_NUMBER')
#     j = ctx.file_ddh_json
#     logger_name = json_mac_dns(j, logger_mac) if logger_mac else ''
#     soft_ver = utils_ddh_get_commit()
#     ddh_vessel_name = json_get_vessel_name(j)
#     t_fmt = '%Y-%m-%d %H:%M:%S'
#     time_local = datetime.datetime.now().strftime(t_fmt)
#     time_utc = datetime.datetime.utcnow().strftime(t_fmt)
#     hw_up = sp.run('uptime -p', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
#     lat = back['gps']['lat']
#     lon = back['gps']['lon']
#
#     _d = {'msg_code': msg_code,
#           'ddh_sn': ddh_sn,
#           'ddh_vessel_name': ddh_vessel_name,
#           'soft_ver': soft_ver,
#           'logger_mac': logger_mac,
#           'logger_name': logger_name,
#           'time_utc': time_utc,
#           'time_local': time_local,
#           'time_sent': '',
#           'ddh_gps_position': '{},{}'.format(lat, lon),
#           'ddh_hardware_uptime': hw_up.stdout.decode()}
#
#     # -------------------------------------
#     # create JSON file that will be pushed
#     # -------------------------------------
#     fol = ctx.dir_dl_files
#     path = '{}/.pusher_{}.json'.format(fol, time.time_ns())
#     with open(path, 'w') as f:
#         json.dump(_d, f)
#     l_i_('[ PUSH ] created file {}'.format(path))
#
#
# # shorter code
# _cb = _create_file_to_be_pushed
#
#
# def notify_ddh_boot():
#     return _cb(CODE_DDH_BOOTED)
#
#
# def notify_ddh_keep_alive():
#     return _cb(CODE_DDH_KEEP_ALIVE)
#
#
# def notify_ddh_support_request():
#     return _cb(CODE_DDH_SUPPORT_REQUEST)
#
#
# def notify_ddh_logger_ok(mac):
#     return _cb(CODE_LOGGER_DOWNLOAD_OK, logger_mac=mac)
#
#
# def notify_ddh_logger_error(mac):
#     return _cb(CODE_LOGGER_DOWNLOAD_ERROR, logger_mac=mac)
#
#
# def notify_ddh_test(mac):
#     return _create_file_to_be_pushed(CODE_TEST, logger_mac=mac)
#
#
#
# import datetime
# import glob
# import json
# import os
# import threading
# import time
# import pusher
# from ddh.threads.utils_logs import l_w_, l_e_, l_i_
# from settings import ctx
#
#
# PUSHER_INTERVAL_SECS = 10
# PUSHER_BLE_INTERVAL_SECS = 120
#
#
# def _push_n_delete_files(cli, files):
#     for _ in files:
#         f = open(_)
#         _d = json.load(f)
#
#         # add time sent, which is != time created
#         _ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         _d['time_sent'] = _ts
#         try:
#             cli.trigger('ddh_active_channel_up',
#                         'ddh_active_event_up',
#                         _d)
#             os.unlink(_)
#             l_i_('[ PUSH ] done file {}'.format(_))
#         except (Exception,) as ex:
#             l_e_('[ PUSH ] file {} exception -> {}'.format(_, ex))
#         f.close()
#
#
# def pusher_init():
#
#     # ----------------------
#     # build pusher client
#     # ----------------------
#     _pi = os.getenv('DDH_PUSHER_APP_ID')
#     _pk = os.getenv('DDH_PUSHER_KEY')
#     _ps = os.getenv('DDH_PUSHER_SECRET')
#     _pc = os.getenv('DDH_PUSHER_CLUSTER')
#     if not _pi or not _pk or not _ps or not _pc:
#         l_e_('[ PUSH ] missing credentials')
#         return
#     _cli = pusher.Pusher(
#         app_id=_pi,
#         key=_pk,
#         secret=_ps,
#         cluster=_pc,
#         ssl=True
#     )
#
#     # --------------------------------------
#     # thread: grab JSON files and push them
#     # --------------------------------------
#     def _th_fxn_push(cli):
#         l_w_('[ PUSH ] thread start')
#         wc = '{}/.pusher_*.json'.format(ctx.dir_dl_files)
#
#         while 1:
#             if back['ble']['downloading']:
#                 l_i_('[ PUSH ] waiting BLE to finish')
#                 time.sleep(PUSHER_BLE_INTERVAL_SECS)
#                 continue
#
#             files = glob.glob(wc)
#             n = len(files)
#             if n:
#                 l_i_('[ PUSH ] {} files to do'.format(n))
#                 _push_n_delete_files(cli, files)
#             time.sleep(PUSHER_INTERVAL_SECS)
#
#     if not ctx.push_en:
#         l_e_('[ PUSH ] no thread, context disabled')
#         return
#     th = threading.Thread(target=_th_fxn_push, args=(_cli, ))
#     th.start()
#
#
# # test
# if __name__ == '__main__':
#     pusher_init()
