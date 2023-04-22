"""Configuration window for Balloon Reminder"""

from pyrevit import forms
from pyrevit import script
from System.Windows.Input import Key


class BalloonReminderConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._config = script.get_config()

        # compact central
        self.compact_central.IsChecked = \
            self._config.get_option('compact_central', False)

        # relinquish objects
        self.relinq_proj_standards.IsChecked = \
            self._config.get_option('relinq_proj_standards', False)

        self.relinq_families.IsChecked = \
            self._config.get_option('relinq_families', False)

        self.relinq_borrowed.IsChecked = \
            self._config.get_option('relinq_borrowed', False)

        self.relinq_views.IsChecked = \
            self._config.get_option('relinq_views', False)

        self.relinq_user_created.IsChecked = \
            self._config.get_option('relinq_user_created', False)

        # sync comment
        self.sync_comment.Text = \
            str(self._config.get_option('sync_comment', ''))

        # save local
        self.save_local.IsChecked = \
            self._config.get_option('save_local', False)

    def sync_comment_keydown(self, sender, key_event_arg):
        if key_event_arg.Key == Key.Enter:
            self.save_options(sender, key_event_arg)

    def save_options(self, sender, args):
        # compact central
        self._config.compact_central = \
            self.compact_central.IsChecked

        # relinquish objects
        self._config.relinq_proj_standards = \
            self.relinq_proj_standards.IsChecked

        self._config.relinq_families = \
            self.relinq_families.IsChecked

        self._config.relinq_borrowed = \
            self.relinq_borrowed.IsChecked

        self._config.relinq_views = \
            self.relinq_views.IsChecked

        self._config.relinq_user_created = \
            self.relinq_user_created.IsChecked

        # sync comment
        self._config.sync_comment = self.sync_comment.Text

        # save local
        self._config.save_local = self.save_local.IsChecked

        script.save_config()
        self.Close()


BalloonReminderConfigWindow('BalloonReminderConfig.xaml').ShowDialog()
