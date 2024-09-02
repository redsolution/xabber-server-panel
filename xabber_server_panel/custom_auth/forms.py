from django.contrib.auth.forms import UsernameField
from django import forms
from django.contrib.auth import authenticate
from xabber_server_panel.api.api import EjabberdAPI
from xabber_server_panel.custom_auth.exceptions import UnauthorizedException


class CustomAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = UsernameField(
        widget=forms.TextInput(
            attrs={
                'autofocus': True,
                'placeholder': 'username@example.com'
            }
        )
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'placeholder': 'Password'
            }
        ),
    )

    def __init__(self, *args, request=None, **kwargs):

        """ add request in arguments to provide it in authenticate func """

        self.request = request
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        super(CustomAuthenticationForm, self).clean()
        self.user = authenticate(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )
        if self.user is None:
            self.add_error(
                None, 'The username and password you have entered is invalid.'
            )


class ApiAuthenticationForm(forms.Form):

    username = UsernameField(
        widget=forms.TextInput(
            attrs={
                'autofocus': True,
                'placeholder': 'username@example.com'
            }
        )
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'placeholder': 'Password'
            }
        ),
    )

    source_browser = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.HiddenInput()
    )
    source_ip = forms.GenericIPAddressField(
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, request=None, **kwargs):
        self.api = EjabberdAPI(request=request)
        self.request = request
        super(ApiAuthenticationForm, self).__init__(*args, **kwargs)

    def after_clean(self):
        self.user = authenticate(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            check_password=False
        )
        if self.user is None:
            self.add_error(
                None, 'The username or password you have entered is invalid.'
            )

    def clean(self):
        super(ApiAuthenticationForm, self).clean()
        if not self.errors:
            try:
                self.api.login(self.cleaned_data)
            except UnauthorizedException:
                self.add_error(
                    None, 'The username or password you have entered is invalid.'
                )

            # check api errors
            if self.api.errors:
                for field, error in self.api.response.items():
                    try:
                        self.add_error(field, error)
                    except ValueError:
                        self.add_error(None, error)
            else:
                self.after_clean()
        return self.cleaned_data