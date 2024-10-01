from django import forms

from jid_validation.utils import validate_host, validate_localpart
from django.contrib.auth.validators import UnicodeUsernameValidator


class InstallationForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.step_errors = {}
        self.steps = {
            1: ['host'],
            2: ['db_host', 'db_name', 'db_user', 'db_user_pass'],
            3: ['username', 'password'],
        }
        super(InstallationForm, self).__init__(*args, **kwargs)

    host = forms.CharField(
        max_length=128,
        label='XMPP host',
        widget=forms.TextInput(attrs={'placeholder': 'example.com'}),
    )
    username = forms.CharField(
        max_length=100,
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': 'admin'}),
        validators=[UnicodeUsernameValidator()]
    )
    password = forms.CharField(
        max_length=100,
        label='Password',
        widget=forms.PasswordInput(
            render_value=True,
            attrs={'placeholder': 'Password'}
        )
    )
    db_host = forms.CharField(
        max_length=100,
        label='Database server name',
        widget=forms.TextInput(attrs={'placeholder': 'localhost'})
    )
    db_name = forms.CharField(
        max_length=100,
        label='Database name',
        widget=forms.TextInput(attrs={'placeholder': 'xabberserver'})
    )
    db_user = forms.CharField(
        max_length=100,
        label='Database user',
        widget=forms.TextInput(attrs={'placeholder': 'admin'}),
    )
    db_user_pass = forms.CharField(
        max_length=100,
        required=False,
        label='Database user password',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )
    base_cronjobs = forms.BooleanField(
        initial=False,
        required=False
    )

    def _validate_field(self, field_name, add_error=False):

        """ Validate concrete form field by field name """

        field = self.fields.get(field_name)
        data = self.data.get(field_name, '')
        if field:
            try:
                field.clean(data)
            except forms.ValidationError as e:
                if add_error:
                    self.step_errors[field_name] = e
                return False

            return True

    def get_step(self, default_step=None, current_step=0):
        for step, fields in self.steps.items():
            add_error = step <= current_step
            for field in fields:
                if not self._validate_field(field, add_error=add_error):
                    return step

        return default_step

    def step_1_errors(self):
        return any(field in self.step_errors.keys() for field in self.steps.get(1, []))

    def step_2_errors(self):
        return any(field in self.step_errors.keys() for field in self.steps.get(2, []))

    def step_3_errors(self):
        return any(field in self.step_errors.keys() for field in self.steps.get(3, []))

    def clean_host(self):
        host = self.cleaned_data['host']
        # validate and normalize host
        result = validate_host(host)
        if result.get('success'):
            host = result.get('host')
        else:
            self.add_error('host', result.get('error_message'))

        return host

    def clean_username(self):
        username = self.cleaned_data['username']

        # validate and normalize circle
        result = validate_localpart(username)
        if result.get('success'):
            username = result.get('localpart')
        else:
            self.add_error('username', result.get('error_message'))

        return username