#!/usr/bin/env bash
LI=/home/pi/li
DDS=$LI/dds


# abort upon any error
clear && echo && set -e
trap 'echo ‘$BASH_COMMAND’ TRAPPED! rv $?' EXIT


# see service output -> sudo journalctl -f -u unit_dds_ble
echo
echo '-----------------------------------------'

echo 'reloading LI DDS BLE service...'
sudo systemctl disable unit_dds_ble.service || true
sudo systemctl enable unit_dds_ble.service
sudo systemctl start unit_dds_ble.service

echo '-----------------------------------------'
echo 'done LI DDS reload BLE service'
echo
