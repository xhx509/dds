#!/usr/bin/env bash
VENV=/home/pi/li/venv
FOL_DDS=/home/pi/li/dds
FOL_DDT=/home/pi/li/ddh_tools


# abort upon any error
echo; echo; set -e; echo
trap 'echo ‘$BASH_COMMAND’ TRAPPED! rv $?; cd $FOL_DDS' EXIT


ping -q -c 1 -W 1 www.google.com
rv=$?
if [ $rv -eq 0 ]; then
    echo;  echo 'R > we have internet, updating...'
    $FOL_DDT/dt_update_python_mat.sh
    $FOL_DDT/dt_update_python_ddh_dds.sh
else
    echo; echo 'R > NO internet, NO updating'
fi


# fill AWS vars
export DDH_AWS_NAME=_AN_
export DDH_AWS_KEY_ID=_AK_
export DDH_AWS_SECRET=_AS_
export DDH_AWS_SNS_TOPIC_ARN=_AT_
export DDH_BOX_SERIAL_NUMBER=_DDH_SN_


echo; echo 'R > bluetooth sanity check'
sudo systemctl restart bluetooth
sudo hciconfig hci0 up



echo; echo 'R > permissions date / bluepy / ifmetric'
BLUEPY_HELPER=$VENV/lib/python3.7/site-packages/bluepy/bluepy-helper
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric
sudo setcap 'cap_net_raw,cap_net_admin+eip' $BLUEPY_HELPER



echo; echo 'R > pseudo-services'
source $VENV/bin/activate
pkill -F /tmp/dds-core.pid || true
pkill -F /tmp/dds-cnv.pid || true
pkill -F /tmp/dds-aws.pid || true
cd $FOL_DDS
$VENV/bin/python main.py &
$VENV/bin/python services/dds_aws_service.py &
$VENV/bin/python services/dds_cnv_service.py &



echo; echo 'R > calling DDS main code'
sudo chown -R pi:pi $FOL_DDS
cd $FOL_DDS && $VENV/bin/python main.py
