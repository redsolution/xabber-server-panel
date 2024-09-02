from django import forms

from jid_validation.utils import validate_jid, validate_host, validate_localpart


class GroupForm(forms.Form):

    localpart = forms.CharField(
        required=True,
    )

    host = forms.CharField(
        required=True
    )

    name = forms.CharField(
        required=True
    )

    owner = forms.CharField(
        required=True,
    )

    privacy = forms.ChoiceField(
        widget=forms.RadioSelect,
        initial='public',
        choices=[
            ('public', 'public'),
            ('incognito', 'incognito'),
        ]
    )

    index = forms.ChoiceField(
        widget=forms.RadioSelect,
        initial='none',
        choices=[
            ('none', 'none'),
            ('local', 'local'),
            ('global', 'global'),
        ]
    )

    membership = forms.ChoiceField(
        widget=forms.RadioSelect,
        initial='open',
        choices=[
            ('open', 'open'),
            ('member-only', 'member-only'),
        ]
    )

    def clean_localpart(self):
        localpart = self.cleaned_data['localpart']

        # validate and normalize localpart
        result = validate_localpart(localpart)
        if result.get('success'):
            localpart = result.get('localpart')
        else:
            self.add_error('localpart', result.get('error_message'))

        return localpart

    def clean_host(self):
        host = self.cleaned_data['host']

        # validate and normalize host
        result = validate_host(host)
        if result.get('success'):
            host = result.get('host')
        else:
            self.add_error('host', result.get('error_message'))

        return host

    def clean_owner(self):
        owner = self.cleaned_data['owner']

        # validate and normalize owner
        result = validate_jid(owner)
        if result.get('success'):
            owner = result.get('full_jid')
        else:
            self.add_error('owner', result.get('error_message'))

        return owner
