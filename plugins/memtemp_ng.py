"""Aligned compact memory, CPU, temperature and frequency HUD."""

import logging

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from PIL import ImageFont
from pwnagotchi.ui.components import Widget
from pwnagotchi.ui.view import BLACK


class _MetricLabeledValue(Widget):
    """Label/value pair positioned from actual font metrics, not character count."""

    def __init__(self, label, value, position, label_font, value_font, gap=1):
        super().__init__(position, BLACK)
        self.label, self.value = label, value
        self.label_font, self.value_font, self.gap = label_font, value_font, gap

    def draw(self, canvas, drawer):
        drawer.text(self.xy, self.label, font=self.label_font, fill=self.color)
        width = int(round(drawer.textlength(self.label, font=self.label_font)))
        drawer.text((self.xy[0] + width + self.gap, self.xy[1]), self.value,
                    font=self.value_font, fill=self.color)


class MemTempNG(plugins.Plugin):
    __author__ = 'Exnuz'
    __version__ = '3.0.0'
    __license__ = 'GPL3'
    __description__ = 'Displays aligned memory, CPU, temperature and frequency values.'

    ALLOWED_FIELDS = {'mem': 'mem_usage', 'cpu': 'cpu_load', 'temp': 'cpu_temp', 'freq': 'cpu_freq'}
    DEFAULT_FIELDS = ('mem', 'cpu', 'temp', 'freq')
    # All labels occupy four character cells, keeping every value aligned.
    DEFAULT_LABELS = {'mem': 'MEM:', 'cpu': 'CPU:', 'temp': 'TEMP', 'freq': 'FREQ'}
    # Labels and values are rendered separately, so there is no approximate
    # character-width calculation.  A five-character temperature fits safely.
    DEFAULT_POSITIONS = {'mem': (197, 80), 'cpu': (197, 87), 'temp': (197, 94), 'freq': (197, 101)}
    VALUE_X_OFFSET = 23

    def on_loaded(self):
        logging.info('[MemTemp_NG] Plugin loaded.')

    def mem_usage(self):
        return '%d%%' % int(pwnagotchi.mem_usage() * 100)

    def cpu_load(self):
        return '%d%%' % int(pwnagotchi.cpu_load() * 100)

    def cpu_temp(self):
        scale = self.options.get('scale', 'celsius').lower()
        temperature = pwnagotchi.temperature()
        if scale == 'fahrenheit':
            return '%.1fF' % ((temperature * 9 / 5) + 32)
        if scale == 'kelvin':
            return '%.1fK' % (temperature + 273.15)
        return '%.1fC' % temperature

    def cpu_freq(self):
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'rt') as stream:
                return '%.1f' % (float(stream.readline()) / 1000000)
        except OSError:
            return '-'

    def on_ui_setup(self, ui):
        self.fields = [field.strip() for field in self.options.get(
            'fields', ','.join(self.DEFAULT_FIELDS)).split(',')
            if field.strip() in self.ALLOWED_FIELDS]
        for field in self.fields:
            configured = self.options.get('%s_position' % field)
            position = tuple(map(int, configured.split(','))) if configured else self.DEFAULT_POSITIONS[field]
            label = self.options.get('%s_label' % field, self.DEFAULT_LABELS[field])
            # The proportional value font removes the visually oversized
            # monospaced cell around decimal points: 42.9C and 1.0 stay tight.
            label_font = fonts.Small
            value_font = fonts.Small
            if field in ('temp', 'freq'):
                label_font = ImageFont.truetype('DejaVuSans.ttf', fonts.Small.size)
                value_font = ImageFont.truetype('DejaVuSans.ttf', fonts.Small.size)
            ui.add_element('memtemp_%s' % field, _MetricLabeledValue(
                label=label, value='-', position=position,
                label_font=label_font, value_font=value_font, gap=1))

    def on_ui_update(self, ui):
        for field in self.fields:
            try:
                value = getattr(self, self.ALLOWED_FIELDS[field])()
            except (OSError, ValueError) as error:
                logging.warning('[MemTemp_NG] Cannot update %s: %s', field, error)
                value = '-'
            ui.set('memtemp_%s' % field, value)

    def on_unload(self, ui):
        with ui._lock:
            for field in getattr(self, 'fields', ()):
                ui.remove_element('memtemp_%s' % field)
