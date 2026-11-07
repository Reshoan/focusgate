#!/bin/bash
# Firewall layer: send all outgoing HTTPS (except from the proxy user) to the local proxy, and block QUIC/HTTP3 so browsers use TCP.
PORT=8443; USER_NAME=focusgate
up() {
  for ipt in iptables ip6tables; do
    command -v $ipt >/dev/null || continue
    $ipt -t nat -N FOCUSGATE 2>/dev/null; $ipt -t nat -F FOCUSGATE
    $ipt -t nat -A FOCUSGATE -m owner --uid-owner $USER_NAME -j RETURN
    $ipt -t nat -A FOCUSGATE -o lo -j RETURN
    $ipt -t nat -A FOCUSGATE -p tcp --dport 443 -j REDIRECT --to-ports $PORT
    $ipt -t nat -C OUTPUT -j FOCUSGATE 2>/dev/null || $ipt -t nat -I OUTPUT -j FOCUSGATE
    $ipt -N FOCUSGATE_F 2>/dev/null; $ipt -F FOCUSGATE_F
    $ipt -A FOCUSGATE_F -m owner --uid-owner $USER_NAME -j RETURN
    $ipt -A FOCUSGATE_F -p udp --dport 443 -j REJECT
    $ipt -C OUTPUT -j FOCUSGATE_F 2>/dev/null || $ipt -I OUTPUT -j FOCUSGATE_F
    $ipt -C INPUT -p tcp --dport $PORT ! -i lo -j DROP 2>/dev/null || $ipt -I INPUT -p tcp --dport $PORT ! -i lo -j DROP
  done
}
down() {
  for ipt in iptables ip6tables; do
    command -v $ipt >/dev/null || continue
    $ipt -t nat -D OUTPUT -j FOCUSGATE 2>/dev/null; $ipt -t nat -F FOCUSGATE 2>/dev/null; $ipt -t nat -X FOCUSGATE 2>/dev/null
    $ipt -D OUTPUT -j FOCUSGATE_F 2>/dev/null; $ipt -F FOCUSGATE_F 2>/dev/null; $ipt -X FOCUSGATE_F 2>/dev/null
    $ipt -D INPUT -p tcp --dport $PORT ! -i lo -j DROP 2>/dev/null
  done
  return 0
}
case "$1" in up) up;; down) down;; *) echo "usage: $0 up|down"; exit 1;; esac
