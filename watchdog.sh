#!/bin/bash
# Runs every few seconds. Restores FocusGate unless a halt was authorized through `focusgate stop|emergency`.
[ -e /run/focusgate/stop-allowed ] && exit 0
systemctl is-active --quiet focusgate || systemctl start focusgate
# service is up but someone flushed the firewall redirect: put it back
if systemctl is-active --quiet focusgate && ! iptables -t nat -C OUTPUT -j FOCUSGATE 2>/dev/null; then
  /opt/focus-gate/fw.sh up
fi
