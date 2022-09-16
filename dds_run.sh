#!/usr/bin/env bash
VENV=/home/pi/li/venv
FOL_DDS=/home/pi/li/dds


# abort upon any error
set -e
trap 'echo ‘$BASH_COMMAND’ TRAPPED! rv $?; cd $FOL_DDS' EXIT


# fill AWS vars
export DDH_AWS_NAME=p-joaquim
export DDH_AWS_KEY_ID=
export DDH_AWS_SECRET=
export DDH_AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:727249356285:demo-kaz-1234567-basics-topic
export DDH_BOX_SERIAL_NUMBER=9999999


echo; echo 'R > bluetooth sanity check'
sudo systemctl restart bluetooth
sudo hciconfig hci0 up


echo; echo 'R > permissions date / ifmetric'
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric


echo; echo 'R > calling DDS main python code'
sudo chown -R pi:pi $FOL_DDS
source $VENV/bin/activate
cd $FOL_DDS && $VENV/bin/python main.py
