#!/usr/bin/env bash


echo; echo 'K > killing DDS core, cnv, aws'
pkill -F /tmp/dds-core.pid || true
pkill -F /tmp/dds-cnv.pid || true
pkill -F /tmp/dds-aws.pid || true
