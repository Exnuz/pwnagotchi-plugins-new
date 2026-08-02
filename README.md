# Pwnagotchi Plugins NG

Plugins and display extensions for [Pwnagotchi NG](https://github.com/Exnuz/pwnagotchi-ng).

## NG plugins

The maintained plugins are in [`plugins/`](plugins/):

- `clock_ng.py` — compact clock and date overlay;
- `memtemp_ng.py` — aligned memory, CPU, temperature and frequency HUD;
- `display_password_ng.py` — local-only display of the latest available SSID/password pair;
- `wpa_sec_ng.py` — deduplicated WPA-sec uploader, one validated capture per BSSID.

Pwnagotchi NG installs these files automatically. For a manual installation, copy only the required `.py` file to Pwnagotchi's custom-plugin directory and enable its matching `main.plugins.<name>.enabled` configuration key.

`QuickDic.py` is retained for backwards compatibility with the earlier plugin collection.
