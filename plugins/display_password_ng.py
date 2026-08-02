"""Compact, local-only display of the last locally available cracked entry."""

import logging
from pathlib import Path

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class DisplayPasswordNG(plugins.Plugin):
    __author__ = 'Exnuz'
    __version__ = '3.0.0'
    __license__ = 'GPL3'
    __description__ = 'Displays the last locally available SSID/password pair.'

    DEFAULT_FIELDS = ('ssid', 'password')
    DEFAULT_LABELS = {'ssid': 'SSID', 'password': 'PASS'}
    DEFAULT_POSITIONS = {'ssid': '40,94', 'password': '40,101'}
    _POTFILE = Path('/root/handshakes/wpa-sec.cracked.potfile')

    def on_loaded(self):
        logging.info('[DisplayPassword_NG] Plugin loaded.')

    def _last_pair(self):
        """Read locally without spawning ``tail`` on every display redraw."""
        try:
            if not self._POTFILE.is_file():
                return '-', '-'
            with self._POTFILE.open('rt', encoding='utf-8', errors='replace') as stream:
                last_line = ''
                for line in stream:
                    if line.strip():
                        last_line = line.rstrip()
            fields = last_line.split(':')
            if len(fields) >= 4:
                return fields[2] or '-', fields[3] or '-'
        except OSError as error:
            logging.warning('[DisplayPassword_NG] Cannot read local potfile: %s', error)
        return '-', '-'

    def on_ui_setup(self, ui):
        self.fields = [field.strip() for field in self.options.get(
            'fields', ','.join(self.DEFAULT_FIELDS)).split(',')
            if field.strip() in self.DEFAULT_FIELDS]
        for field in self.fields:
            position = tuple(map(int, self.options.get(
                '%s_position' % field, self.DEFAULT_POSITIONS[field]).split(',')))
            # Both labels have four characters, so their values start at the
            # same x coordinate. Use the exact same font as the numeric HUD.
            label = self.options.get('%s_label' % field, self.DEFAULT_LABELS[field])
            ui.add_element('display_%s' % field, LabeledValue(
                color=BLACK, label=label, value='-', position=position,
                label_font=fonts.Small, text_font=fonts.Small, label_spacing=-1))

    def on_ui_update(self, ui):
        ssid, password = self._last_pair()
        if 'ssid' in self.fields:
            ui.set('display_ssid', ssid)
        if 'password' in self.fields:
            ui.set('display_password', password)

    def on_unload(self, ui):
        with ui._lock:
            for field in getattr(self, 'fields', ()):
                ui.remove_element('display_%s' % field)
