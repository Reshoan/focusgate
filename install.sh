#!/bin/bash
# Run: sudo ./install.sh   — installs the proxy, CA trust, firewall redirect and systemd service.
set -euo pipefail
[ "$EUID" -eq 0 ] || { echo "run with sudo"; exit 1; }
REAL_USER=${SUDO_USER:?run via sudo from your normal account}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
SRC=$(cd "$(dirname "$0")" && pwd)

apt-get install -y python3-venv libnss3-tools ca-certificates >/dev/null
id focusgate &>/dev/null || useradd --system --home-dir /var/lib/focusgate --create-home --shell /usr/sbin/nologin focusgate

mkdir -p /opt/focus-gate
[ -x /opt/focus-gate/venv/bin/mitmdump ] || { python3 -m venv /opt/focus-gate/venv; /opt/focus-gate/venv/bin/pip install -q mitmproxy; }
install -m 755 -o root -g root "$SRC/fw.sh" /opt/focus-gate/fw.sh
install -m 644 -o root -g root "$SRC/gate.py" "$SRC/rules.py" /opt/focus-gate/
install -m 755 -o root -g root "$SRC/focusgate" /usr/local/bin/focusgate
install -m 644 "$SRC/focusgate.service" /etc/systemd/system/focusgate.service

# Generate the CA as the proxy user, then trust it
CONF=/var/lib/focusgate/mitmproxy
if [ ! -f $CONF/mitmproxy-ca-cert.pem ]; then
  sudo -u focusgate timeout 6 /opt/focus-gate/venv/bin/mitmdump -q --set confdir=$CONF -p 18999 || true
fi
chmod 700 /var/lib/focusgate
install -m 644 $CONF/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/focusgate.crt
update-ca-certificates >/dev/null

# Firefox: enterprise policy (non-removable from the UI) + each profile's cert DB (covers snap installs)
mkdir -p /etc/firefox/policies
cat > /etc/firefox/policies/policies.json <<POL
{"policies":{"Certificates":{"ImportEnterpriseRoots":true,"Install":["/usr/local/share/ca-certificates/focusgate.crt"]}}}
POL
# Chromium family (Brave, Chrome): user NSS db
sudo -u "$REAL_USER" mkdir -p "$REAL_HOME/.pki/nssdb"
[ -f "$REAL_HOME/.pki/nssdb/cert9.db" ] || sudo -u "$REAL_USER" certutil -N -d "sql:$REAL_HOME/.pki/nssdb" --empty-password
sudo -u "$REAL_USER" certutil -A -d "sql:$REAL_HOME/.pki/nssdb" -n focusgate -t "C,," -i /usr/local/share/ca-certificates/focusgate.crt
for db in $(find "$REAL_HOME/.mozilla/firefox" "$REAL_HOME/snap/firefox/common/.mozilla/firefox" -name cert9.db 2>/dev/null); do
  sudo -u "$REAL_USER" certutil -A -d "sql:$(dirname "$db")" -n focusgate -t "C,," -i /usr/local/share/ca-certificates/focusgate.crt
done

systemctl daemon-reload
systemctl enable --now focusgate
echo "Done. Fully restart your browsers. Check: focusgate status"
