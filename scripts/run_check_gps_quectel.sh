#!/usr/bin/env bash

VENV=/home/pi/li/venv
FOL_SCR=/home/pi/li/dds/dds


clear
printf '\nR> run GPS quectel script \n'
source $VENV/bin/activate
$VENV/bin/python $FOL_SCR/gps.py
