# FocusGate

Path-level website blocking for Linux that is hard to bypass from the browser.
Current rules (edit `rules.py`):
- **YouTube:** homepage, feeds and Shorts blocked; search and videos work. On watch pages the sidebar recommendations and end cards are hidden and autoplay is switched off.
- **Instagram:** only messages, single posts/reels, stories and individual profiles. Feed, Explore and the Reels feed are blocked.
- **Facebook:** only messages, notifications, individual profiles and single posts/videos/reels. Home, Reels, Watch, Marketplace, Groups etc. are blocked.

## How it works
- A mitmproxy (`gate.py`) runs as a dedicated system user (`focusgate`) and sees full HTTPS URLs.
- `fw.sh` uses iptables to redirect all outgoing HTTPS from other users to the proxy and blocks QUIC (UDP 443).
- The proxy blocks matching document loads and injects a small guard script to catch in-page (SPA) navigation.
- Rules live in `rules.py`. Edit them to add or change sites.
- `sudo focusgate stop` starts a random 5-15 minute wait with reminders to reconsider (Ctrl+C cancels). When it ends, FocusGate halts until the next reboot, when it comes back by itself.
- `sudo focusgate emergency` halts it immediately, but only after typing a freshly generated pledge (about 360 words) word for word. Finishing in under 3 minutes is rejected.
- A watchdog timer (every 5 s) restarts the service, and repairs the firewall redirect, unless the halt was authorized by one of the commands above. So a plain `systemctl stop focusgate` gets undone within seconds.
- `sudo focusgate start` re-enables it early. Halts and attempts are logged in `/var/lib/focusgate/events.log`.

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
- Anyone with root can still disable it by stopping both `focusgate.service` and `focusgate-watchdog.timer`, or editing `/opt/focus-gate`. The timer and pledge add friction, they don't make it impossible. Removing yourself from sudo is the only complete fix.
- Redirects all port-443 traffic through the proxy; non-target hosts pass through untouched.
- Instagram and Facebook change their internals often; the in-page guard and the YouTube sidebar/autoplay selectors may need tweaks over time.
- Hiding the YouTube sidebar and autoplay works by editing the page, so it depends on YouTube's current element names.

## Uninstall
```bash
sudo focusgate stop
sudo systemctl disable focusgate && sudo rm -rf /etc/systemd/system/focusgate.service /opt/focus-gate /usr/local/bin/focusgate /usr/local/share/ca-certificates/focusgate.crt /etc/firefox/policies/policies.json
sudo update-ca-certificates --fresh && sudo userdel -r focusgate
```
Also remove the `focusgate` cert from `~/.pki/nssdb` (`certutil -D -d sql:$HOME/.pki/nssdb -n focusgate`) and from Firefox profiles.
