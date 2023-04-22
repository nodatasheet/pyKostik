"""Configuration window"""

import re
from pyrevit import forms
from pyrevit import script
from System.Windows.Input import Key


class DistributionOption:
    def __init__(self, display_text, distribution_opt):
        # type: (str, str) -> None
        self._display_text = display_text
        self._distribution_opt = distribution_opt

    @property
    def display_text(self):
        return self._display_text

    @property
    def distribution_opt(self):
        return self._distribution_opt


distribution_opts = [DistributionOption('Left To Right', 'left_to_right'),
                     DistributionOption('Top To Bottom', 'top_to_bottom'),
                     DistributionOption('Bottom To Top', 'bottom_to_top')]


class ConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._config = script.get_config()

        self.distribute_comps_cb.ItemsSource = distribution_opts
        self.distribute_comps_cb.SelectedItem = \
            self.get_current_distribution_opt()

        self.gap_btw_components.Text = \
            str(self._config.get_option('gap_btw_components', 0))

    def get_current_distribution_opt(self):
        legcomps_distribution = \
            self._config.get_option('legcomps_distribution', 0)
        for opt in distribution_opts:
            if opt.distribution_opt == legcomps_distribution:
                return opt
        else:
            return distribution_opts[0]

    def gap_btw_components_preview(self, sender, t):
        """Restrict input to number"""
        # TODO: restrict using several dots and minus symbols
        re_pattern = re.compile(r'^\d*[.-]?\d*$')
        t.Handled = not(re_pattern.match(t.Text))

    def gap_btw_components_keydown(self, sender, key_event_arg):
        if key_event_arg.Key == Key.Enter:
            self.save_options(sender, key_event_arg)

    def _is_number(self, input_str):
        is_number = True
        try:
            float(input_str)
        except ValueError:
            is_number = False
        return is_number

    def save_options(self, sender, args):
        # replace blank text by zero
        if not self.gap_btw_components.Text:
            self.gap_btw_components.Text = str(0)

        # text is number validation
        if self._is_number(self.gap_btw_components.Text):

            self._config.gap_btw_components = \
                float(self.gap_btw_components.Text)

            self._config.legcomps_distribution = \
                self.distribute_comps_cb.SelectedItem.distribution_opt

            script.save_config()
            self.Close()

        else:
            forms.alert('Input should be a number')


config_window = ConfigWindow('LegendCreateComponents_ui.xaml')
config_window.ShowDialog()
