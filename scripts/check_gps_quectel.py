#!/usr/bin/env python3
import argparse

import time
import serial
import sys
from serial import SerialException
from mat.utils import PrintColors as PC


# hardcoded, since they are FIXED on SixFab hats

PORT_CTRL = '/dev/ttyUSB2'
PORT_DATA = '/dev/ttyUSB1'


def _coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format
    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = '{}.{}'.format(head[-2:], x[1])
    decimal = int(deg) + float(minutes) / 60
    return decimal


def _gps_configure_quectel() -> int:
    """ only needed once, configures Quectel GPS via USB and closes port """
    rv = 0
    sp = None
    try:
        sp = serial.Serial(PORT_CTRL, baudrate=115200, timeout=0.5)
        # ensure GPS disabled, try to enable it
        sp.write(b'AT+QGPSEND\r\n')
        sp.write(b'AT+QGPSEND\r\n')
        sp.write(b'AT+QGPS=1\r\n')
        # ignore echo
        sp.readline()
        ans = sp.readline()
        rv = 0 if ans == b'OK\r\n' else 2
        # errors: 504 (already on), 505 (not activated)
        if ans.startswith(b'+CME ERROR: '):
            rv = ans.decode()[-3]
    except (FileNotFoundError, SerialException) as ex:
        rv = 1
    finally:
        if sp:
            sp.close()
        return rv


if __name__ == '__main__':

    # -n 1: infinite loop, -n 0: only once
    ap = argparse.ArgumentParser(description='Test the GPS Quectel in Raspberry')
    ap.add_argument('-n', action='store', choices=['0', '1'], required=True)
    args = ap.parse_args()

    # inform of command parameters
    print('[ in ] GPS Quectel test infinite mode {}'.format(args.n))

    # try to enable GPS port
    retries = 0
    while 1:
        if retries == 3:
            e = '[ ER ] GPS Quectel failure init, retry {}'
            print(e.format(retries + 1))
            sys.exit(1)
        if _gps_configure_quectel() == 0:
            print('[ OK ] GPS Quectel initialization success')
            break
        time.sleep(1)

    # banner
    _till, ns = 20, 0
    s = '\n[ .. ] Wait frames for {} s / loop, n = {}'
    print(s.format(_till, args.n))

    # super-loop: infinite mode or not
    sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.1)
    while 1:
        try:
            _start = time.perf_counter()
            _till = time.perf_counter() + _till

            # loop: frame timeout
            while True:
                if time.perf_counter() > _till:
                    print('[ ER ] GPS Quectel, could not get any data frame')
                    time.sleep(.1)
                    continue

                # reading serial port
                data = sp.readline()
                if b'$GPGGA' in data:
                    gga = data.decode()
                    s = gga.split(',')
                    # index 6: quality indicator, 7: num of satellites
                    # if s[6] in ('1', '2'):
                    #    ns = int(s[7])
                    ns = int(s[7])
                    print('[ OK ] GGA number satellites', ns)

                if b'$GPRMC' in data:
                    rmc = data.decode()
                    s = rmc.split(",")
                    if s[2] == 'V':
                        continue
                    if s[3] and s[5]:
                        print('[ -> ] {}'.format(rmc), end='')
                        lat, lon = _coord_decode(s[3]), _coord_decode(s[5])
                        print('[ OK ] RMC data: {}, {}'.format(lat, lon))
                        _took = time.perf_counter() - _start
                        PC.G('[ OK ] took: {:.2f} seconds, #sats {}'.format(_took, ns))
                        break

            # use the command-line argument
            if int(args.n) == 0:
                print('[ .. ] GPS test only had to run once, leaving!')
                break

        except SerialException as se:
            print(se)
            break

    # clean-up
    if sp:
        sp.close()

 
