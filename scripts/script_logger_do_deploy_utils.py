import json
import time
import bluepy.btle as ble
from bluepy.btle import Scanner
from mat.ble.bluepy.cc26x2r_logger_controller import LoggerControllerCC26X2R
from mat.utils import PrintColors as PC


class ScriptException(Exception):
    pass


def _die_if(condition, where):
    if condition:
        raise ScriptException(where)


def _ensure_wake_mode_is_on(lc):
    rv = lc.ble_cmd_wak()
    if rv == b'ERR':
        return rv
    if rv == 'on':
        return True

    rv = lc.ble_cmd_wak()
    if rv == b'ERR':
        return rv

    return rv == 'on'


def get_script_cfg_file():
    # here it is OK to crash to detect valid json files
    with open('script_logger_do_deploy_cfg.json') as f:
        return json.load(f)


def set_script_cfg_file_do_value(cfg_d: dict):
    with open('script_logger_do_deploy_cfg.json', 'w') as f:
        return json.dump(cfg_d, f)


def deploy_logger(mac, sn, flag_run):
    lc = LoggerControllerCC26X2R(mac)

    try:
        if lc.open():

            rv = lc.ble_cmd_gfv()
            print('\t\tGFV --> {}'.format(rv))

            rv = lc.ble_cmd_sts()
            print('\t\tSTS --> {}'.format(rv))
            _die_if(not rv or rv == 'error', 'sts')

            lc.ble_cmd_led()
            print('\t\tLED --> blinked!')

            rv = lc.ble_cmd_stp()
            print('\t\tSTP --> {}'.format(rv))
            _die_if(not rv, 'stp')

            rv = lc.ble_cmd_stm()
            print('\t\tSTM --> {}'.format(rv))
            _die_if(not rv, 'stm')

            rv = lc.ble_cmd_gtm()
            print('\t\tGTM --> {}'.format(rv))
            _die_if(not rv, 'gtm')

            rv = lc.ble_cmd_frm()
            print('\t\tFRM --> {}'.format(rv))
            _die_if(not rv, 'frm')

            d = get_script_cfg_file()
            rv = lc.ble_cmd_cfg(d)
            print('\t\tCFG --> {}'.format(rv))
            _die_if(not rv, 'cfg')

            rv = lc.ble_cmd_wli('BA8007')
            print('\t\tWLI (BA) --> {}'.format(rv))
            _die_if(not rv, 'wli_ba')

            rv = lc.ble_cmd_wli('MA1234ABC')
            print('\t\tWLI (MA) --> {}'.format(rv))
            _die_if(not rv, 'wli_ma')

            rv = lc.ble_cmd_wli('CA1234')
            print('\t\tWLI (CA) --> {}'.format(rv))
            _die_if(not rv, 'wli_ca')

            s = 'SN{}'.format(sn)
            rv = lc.ble_cmd_wli(s)
            print('\t\tWLI (SN) --> {}'.format(rv))
            _die_if(not rv, 'wli_sn')

            rv = lc.ble_cmd_rli()
            print('\t\tRLI --> {}'.format(rv))

            rv = _ensure_wake_mode_is_on(lc)
            print('\t\tWAK --> {}'.format(rv))
            _die_if(not rv, 'wak')

            rv = lc.ble_cmd_gdo()
            print('\t\tGDO --> {}'.format(rv))
            _die_if(not rv[0] or rv[0] == '0000', 'check oxygen sensor')

            # -------------------------------
            # RUNs logger, depending on flag
            # -------------------------------
            if flag_run:
                time.sleep(1)
                rv = lc.ble_cmd_rws('LAB LAB')
                print('\t\tRWS --> {}'.format(rv))
                _die_if(not rv, 'rws')
            else:
                print('\t\tRWS --> omitted: current flag value is False')

            lc.close()
            return 0

    except ble.BTLEException as ex:
        e = '[ BLE ] exception -> {}'.format(ex)
        print(PC.FAIL + '\t{}'.format(e) + PC.ENDC)
        lc.close()
        return 1

    except ScriptException as se:
        e = 'error -> script exception -> {}'.format(se)
        print(PC.FAIL + '\t{}'.format(e) + PC.ENDC)
        lc.close()
        return 1


# BLE scan returning 2 dictionaries: near & far
def get_ordered_scan_results() -> tuple:
    till = 6
    s = 'detecting nearby loggers, please wait {} seconds...'
    print(PC.OKBLUE + s.format(till) + PC.ENDC)

    sr = Scanner().scan(float(till))

    # bluepy 'scan results (sr)' format -> friendlier one
    sr_f = {each_sr.addr: (each_sr.rssi, each_sr.rawData) for each_sr in sr}

    # ----------------------------------------------
    # filter: only keep lowell instruments' loggers
    # ----------------------------------------------
    _do1, _do2 = {}, {}
    for k, v in sr_f.items():
        try:
            if v[1]:
                if b'DO-1' in v[1]:
                    _do1[k] = v[0]
                if b'DO-2' in v[1]:
                    _do2[k] = v[0]
        except TypeError:
            continue

    sr_f = _do1
    sr_f.update(_do2)

    # nearest: the highest value, less negative
    sr_f_near = sorted(sr_f.items(), key=lambda x: x[1], reverse=True)
    sr_f_far = sorted(sr_f.items(), key=lambda x: x[1], reverse=False)
    return sr_f_near, sr_f_far
