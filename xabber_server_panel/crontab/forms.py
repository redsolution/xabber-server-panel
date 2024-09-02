from django import forms
from ast import literal_eval
from django.core.exceptions import ValidationError
import json

from .models import CronJob


def base_commands_choices():
    return CronJob.objects.filter(type='built_in_job').values_list('command', 'command')


class CronJobForm(forms.ModelForm):

    class Meta:
        model = CronJob
        fields = '__all__'

    base_command = forms.ChoiceField(
        choices=base_commands_choices,
        required=False
    )

    def clean_base_command(self):
        base_command = self.cleaned_data.get('base_command')
        command = self.cleaned_data.get('command')

        if not base_command and not command:
            self.add_error('command', 'This field is required')
        elif base_command:
            self.cleaned_data['command'] = base_command

        return base_command

    def clean_args(self):
        args = self.cleaned_data.get('args')
        if args:
            args = args.strip()
            try:
                args_list = literal_eval(args)
                if not isinstance(args_list, list):
                    raise ValidationError('Args must be in the format of a list.')
            except (ValueError, SyntaxError):
                raise ValidationError('Invalid format for args. Must be a valid Python list.')
        return args

    def clean_kwargs(self):
        kwargs = self.cleaned_data.get('kwargs')
        if kwargs:
            kwargs = kwargs.strip()
            try:
                json.loads(kwargs)
            except json.JSONDecodeError:
                raise ValidationError('Invalid format for kwargs. Must be a valid JSON string.')
        return kwargs