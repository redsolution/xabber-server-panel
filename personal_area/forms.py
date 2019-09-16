from django import forms

from api.forms import AuthorizedApiForm
from virtualhost.forms import AuthorizedApiForm


class ChangeUserPasswordForm(AuthorizedApiForm):
    api_method = 'change_password_api'

    old_password = forms.CharField(
        max_length=50,
        required=True,
        label='Old password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Old password'})
    )

    password = forms.CharField(
        max_length=50,
        required=True,
        label='Password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )

    confirm_password = forms.CharField(
        max_length=50,
        required=True,
        label='Confirm password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Confirm password'})
    )

    def __init__(self, *args, **kwargs):
        self.user_to_change = kwargs.pop('user_to_change', None)
        super(ChangeUserPasswordForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def before_clean(self):
        username = self.user_to_change.username
        host = self.user_to_change.host
        old_password = self.cleaned_data.get('old_password')
        if not self.user.api.check_user_password({
                'user': username,
                'host': host,
                'password': old_password
            }):
            self.add_error(None, 'Invalid old password')
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password == confirm_password:
            self.cleaned_data.pop('password')
            self.cleaned_data.pop('confirm_password')
            self.cleaned_data['newpass'] = password
        else:
            self.add_error(None, 'Passwords do not match.')
        self.cleaned_data['user'] = username
        self.cleaned_data['host'] = host