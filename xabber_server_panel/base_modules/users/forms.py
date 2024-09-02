from django import forms
from django.contrib.auth.hashers import make_password
from datetime import datetime

from jid_validation.utils import validate_host, validate_localpart
from xabber_server_panel.base_modules.users.models import User


class UserForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = User

    # fields to combine date and time to expires
    expires_date = forms.DateField(
        required=False
    )
    expires_time = forms.TimeField(
        required=False
    )

    def save(self, commit=True):

        """ Customized to fix password saving """

        instance = super().save(commit=False)
        password = self.cleaned_data.get('password')

        if password:
            instance.password = make_password(password)  # Hash the password
        if commit:
            instance.save()
        return instance

    def clean(self):

        """
            Customized to:
             * combine expires date and time
        """

        cleaned_data = super().clean()

        # combine expires
        expires_date = cleaned_data.get("expires_date")
        expires_time = cleaned_data.get("expires_time")

        if expires_date:

            # set default time if it's not provided
            if not expires_time:
                expires_time = '12:00'
                expires_time = datetime.strptime(expires_time, '%H:%M').time()

            # Combine date and time
            expires_datetime = datetime.combine(expires_date, expires_time)
            cleaned_data["expires"] = expires_datetime

        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data['username']

        # validate and normalize circle
        result = validate_localpart(username)
        if result.get('success'):
            username = result.get('localpart')
        else:
            self.add_error('username', result.get('error_message'))

        return username

    def clean_host(self):
        host = self.cleaned_data['host']

        # validate and normalize host
        result = validate_host(host)
        if result.get('success'):
            host = result.get('host')
        else:
            self.add_error('host', result.get('error_message'))

        return host