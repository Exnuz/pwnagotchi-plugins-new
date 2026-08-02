import datetime
import logging

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class ClockNG(plugins.Plugin):
    __author__ = 'Exnuz'
    __version__ = '3.0.0'
    __license__ = 'GPL3'
    __description__ = 'Clock/date overlay for Pwnagotchi NG.'

    def on_loaded(self):
        logging.info('[Clock_NG] Plugin loaded.')

    def on_ui_setup(self, ui):
        time_pos = tuple(map(int, self.options.get('time_position', '-5,94').replace(' ', '').split(',')))
        date_pos = tuple(map(int, self.options.get('date_position', '-5,101').replace(' ', '').split(',')))
        ui.add_element('clock_date', LabeledValue(color=BLACK, label='', value='-/-/-', position=date_pos,
                                                   label_font=fonts.Small, text_font=fonts.Small))
        ui.add_element('clock_time', LabeledValue(color=BLACK, label='', value='--:--:--', position=time_pos,
                                                   label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        now = datetime.datetime.now()
        ui.set('clock_date', now.strftime('%d/%m/%y'))
        ui.set('clock_time', now.strftime('%H:%M:%S'))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('clock_date')
            ui.remove_element('clock_time')
