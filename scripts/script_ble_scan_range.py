#!/usr/bin/env python

from bluepy.btle import Scanner, DefaultDelegate
import sys


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


def scan(h, m):
    m = m.replace('-', ':')
    scanner = Scanner(iface=h).withDelegate(ScanDelegate())

    while 1:
        devs = scanner.scan(1.0)
        for d in devs:
            if m == 'all' or m in d.addr:
                s = '{}\t->\t{}\t->\t{}'
                print(s.format(d.addr, d.rssi, d.scanData))


if __name__ == '__main__':
    print('usage: ./program hci_num mac')
    if sys.argv[1] not in '01':
        print('bad parameter hci_num')
        exit(1)

    if sys.argv[2] != 'all' and len(sys.argv[2]) != 17:
        print('bad parameter mac')
        exit(1)

    # SN18106C9: 00-1e-c0-4d-bf-c9
    hci = sys.argv[1]
    mac_mask = sys.argv[2]
    scan(hci, mac_mask)
