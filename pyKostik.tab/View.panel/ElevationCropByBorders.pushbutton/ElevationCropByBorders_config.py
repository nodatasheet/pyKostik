"""Configuration window for Crop tool."""

import re
from pyrevit import forms
from pyrevit import script
from System.Windows.Input import Key


class ElevationCropByBordersConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._config = script.get_config()

        # vertical
        self.walls.IsChecked = \
            self._config.get_option('walls', True)
        self.grids.IsChecked = \
            self._config.get_option('grids', True)

        # horizontal
        self.ceilings.IsChecked = \
            self._config.get_option('ceilings', True)
        self.floors.IsChecked = \
            self._config.get_option('floors', True)
        self.levels.IsChecked = \
            self._config.get_option('levels', True)

        # crop offset
        self.crop_offset.Text = \
            str(self._config.get_option('crop_offset', 0))

    def crop_offset_preview(self, sender, t):
        # restrict input to number
        # TODO: restrict using several dots and minus symbols
        re_pattern = re.compile(r'^\d*[.-]?\d*$')
        t.Handled = not(re_pattern.match(t.Text))

    def crop_offset_keydown(self, sender, key_event_arg):
        if key_event_arg.Key == Key.Enter:
            self.save_options(sender, key_event_arg)

    def set_all(self, state):
        self.walls.IsChecked = state
        self.grids.IsChecked = state
        self.ceilings.IsChecked = state
        self.floors.IsChecked = state
        self.levels.IsChecked = state

    def check_all(self, sender, args):
        self.set_all(True)

    def check_none(self, sender, args):
        self.set_all(False)

    def _is_number(self, input_str):
        is_number = True
        try:
            float(input_str)
        except ValueError:
            is_number = False
        return is_number

    def save_options(self, sender, args):
        # vertical
        self._config.walls = self.walls.IsChecked
        self._config.grids = self.grids.IsChecked

        # horizontal
        self._config.ceilings = self.ceilings.IsChecked
        self._config.floors = self.floors.IsChecked
        self._config.levels = self.levels.IsChecked

        # replace blank text by zero
        if not self.crop_offset.Text:
            self.crop_offset.Text = str(0)

        # text is number validation
        if self._is_number(self.crop_offset.Text):
            self._config.crop_offset = float(self.crop_offset.Text)
            script.save_config()
            self.Close()
        else:
            forms.alert('Input should be a number')


ElevationCropByBordersConfigWindow('ElevationCropByBorders.xaml').ShowDialog()
