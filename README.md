# FocusGate

Path-level website blocking for Linux that is hard to bypass from the browser.
Example setup: block the YouTube homepage, feed and Shorts but keep search and videos; allow only Instagram DMs.

## How it works
- A mitmproxy (`gate.py`) runs as a dedicated system user (`focusgate`) and sees full HTTPS URLs.
- `fw.sh` uses iptables to redirect all outgoing HTTPS from other users to the proxy and blocks QUIC (UDP 443).
- The proxy blocks matching document loads and injects a small guard script to catch in-page (SPA) navigation.
- Rules live in `rules.py`. Edit them to add or change sites.
- `sudo focusgate stop` requires a 60 s wait plus a typing challenge.

## Install (Debian/Ubuntu, systemd)
```bash
git clone https://github.com/Reshoan/focusgate.git
cd focusgate
sudo ./install.sh
```
Then fully restart your browsers. Check with `focusgate status`.

## Update rules
```bash
sudo install -m 644 rules.py gate.py /opt/focus-gate/ && sudo systemctl restart focusgate
```

## Caveats
- Installs a local CA into the system store, Firefox and the Chromium NSS db so the proxy can read HTTPS. The key is readable only by the `focusgate` user.
- Anyone with sudo can still run `systemctl stop focusgate`. Remove yourself from sudo to close that.
- Redirects all port-443 traffic through the proxy; non-target hosts pass through untouched.
- Instagram's internals change; the in-page guard may need rule tweaks over time.

## Uninstall
```bash
sudo focusgate stop
sudo systemctl disable focusgate && sudo rm -rf /etc/systemd/system/focusgate.service /opt/focus-gate /usr/local/bin/focusgate /usr/local/share/ca-certificates/focusgate.crt /etc/firefox/policies/policies.json
sudo update-ca-certificates --fresh && sudo userdel -r focusgate
```
Also remove the `focusgate` cert from `~/.pki/nssdb` (`certutil -D -d sql:$HOME/.pki/nssdb -n focusgate`) and from Firefox profiles.
