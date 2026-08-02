"""Local-first WPA-sec uploader: one validated capture per access point."""

import json
import logging
import os
from pathlib import Path
import re
import time
from threading import Lock

import requests

import pwnagotchi.plugins as plugins
from pwnagotchi.utils import remove_whitelisted


_MAC_RE = re.compile(r'([0-9a-fA-F]{12})')


def _bssid_from_path(path):
    matches = _MAC_RE.findall(Path(path).stem)
    return matches[-1].lower() if matches else ''


class WpaSecNG(plugins.Plugin):
    __author__ = 'Pwnagotchi NG contributors'
    __version__ = '1.1.0'
    __license__ = 'GPL3'
    __description__ = 'Uploads one validated PCAP per BSSID to WPA-sec, without duplicates.'

    _STATE = Path('/var/lib/pwnagotchi/wpa-sec-ng.json')

    def __init__(self):
        self._lock = Lock()
        self._next_attempt = 0.0
        self._state = {'reported_bssids': []}

    def on_loaded(self):
        try:
            self._STATE.parent.mkdir(parents=True, exist_ok=True)
            if self._STATE.exists():
                self._state = json.loads(self._STATE.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            logging.warning('[wpa_sec_ng] state reset: %s', error)
            self._state = {'reported_bssids': []}
        self._migrate_legacy_state()
        logging.info('[wpa_sec_ng] loaded; uploads are deduplicated by BSSID')

    def _migrate_legacy_state(self):
        """Prevent re-sending files which the legacy plugin already recorded."""
        try:
            payload = json.loads(Path('/root/.wpa_sec_uploads').read_text(encoding='utf-8'))
            known = set(self._state.get('reported_bssids', []))
            known.update(filter(None, (_bssid_from_path(path) for path in payload.get('reported', []))))
            self._state['reported_bssids'] = sorted(known)
            self._save_state()
        except (OSError, ValueError, AttributeError):
            pass

    def _save_state(self):
        temporary = self._STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(self._state, sort_keys=True), encoding='utf-8')
        os.replace(temporary, self._STATE)

    @staticmethod
    def _credentials(agent):
        # Reuse the existing wpa-sec key/URL; no secret is copied to a second key.
        return agent.config().get('main', {}).get('plugins', {}).get('wpa-sec', {})

    def _candidates(self, agent, credentials):
        """Return one newest capture for every BSSID not sent before.

        A capture is marked only after WPA-sec accepts it.  Therefore an
        interrupted upload remains eligible for a later retry.
        """
        directory = Path(agent.config()['bettercap']['handshakes'])
        paths = remove_whitelisted([str(path) for path in directory.glob('*.pcap')],
                                   credentials.get('whitelist', []))
        groups = {}
        for path in paths:
            bssid = _bssid_from_path(path)
            if bssid:
                groups.setdefault(bssid, []).append(path)
        reported = set(self._state.get('reported_bssids', []))
        pending = [(bssid, max(items, key=os.path.getmtime))
                   for bssid, items in groups.items() if bssid not in reported]
        return sorted(pending, key=lambda item: os.path.getmtime(item[1]))

    @staticmethod
    def _upload(path, credentials):
        with open(path, 'rb') as capture:
            response = requests.post(credentials['api_url'], cookies={'key': credentials['api_key']},
                                     files={'file': capture}, timeout=30)
        response.raise_for_status()

    @staticmethod
    def _download_results(directory, credentials):
        if not credentials.get('download_results', False):
            return
        output = Path(directory) / 'wpa-sec.cracked.potfile'
        if output.exists() and time.time() - output.stat().st_mtime < 3600:
            return
        url = credentials['api_url'].rstrip('/') + '/?api&dl=1'
        response = requests.get(url, cookies={'key': credentials['api_key']}, timeout=30)
        response.raise_for_status()
        temporary = output.with_suffix('.tmp')
        temporary.write_bytes(response.content)
        os.replace(temporary, output)
        logging.info('[wpa_sec_ng] refreshed local results file')

    def on_internet_available(self, agent):
        if self._lock.locked() or time.monotonic() < self._next_attempt:
            return
        credentials = self._credentials(agent)
        if not credentials.get('api_key') or not credentials.get('api_url'):
            logging.warning('[wpa_sec_ng] credentials are incomplete')
            return
        with self._lock:
            try:
                candidates = self._candidates(agent, credentials)
                if candidates:
                    agent.view().on_uploading('wpa-sec: uploading APs')
                for bssid, path in candidates:
                    self._upload(path, credentials)
                    self._state['reported_bssids'] = sorted(
                        set(self._state.get('reported_bssids', [])) | {bssid})
                    self._save_state()
                    logging.info('[wpa_sec_ng] uploaded validated capture for BSSID %s', bssid)
                if candidates:
                    logging.info('[wpa_sec_ng] upload cycle completed: %d unique AP(s)', len(candidates))
                self._download_results(agent.config()['bettercap']['handshakes'], credentials)
            except (OSError, requests.RequestException) as error:
                retry = max(30, int(self.options.get('retry_seconds', 300)))
                self._next_attempt = time.monotonic() + retry
                logging.warning('[wpa_sec_ng] upload deferred for %ds: %s', retry, error)
            finally:
                agent.view().on_normal()
