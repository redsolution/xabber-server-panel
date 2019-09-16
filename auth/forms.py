from django import forms
from django.contrib.auth import authenticate

from api.forms import ApiForm


class LoginForm(ApiForm):
    api_method = 'login'

    username = forms.CharField(
        max_length=100,
        required=True,
        label='Username *',
        widget=forms.TextInput(attrs={
            'autofocus': '',
            'placeholder': 'username@example.com'
        })
    )

    password = forms.CharField(
        max_length=50,
        required=True,
        label='Password *',
        widget=forms.PasswordInput(render_value=True,
                                   attrs={'placeholder': 'Password'})
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

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def after_clean(self, cleaned_data):
        self.user = authenticate(api=self.api)
        if self.user is None:
            self.add_error(None, 'The username and password you have entered '
                                 'is invalid.')


class LoginFormViaDjango(forms.Form):
    username = forms.CharField(
        max_length=100,
        required=True,
        label='Username *',
        widget=forms.TextInput(attrs={
            'autofocus': '',
            'placeholder': 'username@example.com'
        })
    )

    password = forms.CharField(
        max_length=50,
        required=True,
        label='Password *',
        widget=forms.PasswordInput(render_value=True,
                                   attrs={'placeholder': 'Password'})
    )

    def __init__(self, *args, **kwargs):
        super(LoginFormViaDjango, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def clean(self):
        super(LoginFormViaDjango, self).clean()
        self.user = authenticate(username=self.cleaned_data['username'],
                                 password=self.cleaned_data['password'])
        if self.user is None:
            self.add_error(None, 'The username and password you have entered '
                                 'is invalid.')
