from django import forms

from jid_validation.utils import validate_host, validate_localpart

from .models import Circle


class CircleForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = Circle

    autoshare = forms.BooleanField(
        required=False
    )

    def save(self, commit=True):
        """
            Customized to use circle instead of name
            if name is not provided
        """

        instance = super().save(commit=False)

        # Check if the "name" field is empty
        if not instance.name:
            # Set "name" value from the "circle" field
            instance.name = self.cleaned_data.get('circle')

        autoshare = self.cleaned_data.get('autoshare')
        if autoshare:
            instance.subscribes = self.cleaned_data.get('circle')

        if commit:
            instance.save()

        return instance

    def clean_circle(self):

        circle = self.cleaned_data['circle']

        # validate and normalize circle
        result = validate_localpart(circle)
        if result.get('success'):
            circle = result.get('localpart')
        else:
            self.add_error('circle', result.get('error_message'))

        return circle

    def clean_host(self):
        host = self.cleaned_data['host']

        # validate and normalize host
        result = validate_host(host)
        if result.get('success'):
            host = result.get('host')
        else:
            self.add_error('host', result.get('error_message'))

        return host