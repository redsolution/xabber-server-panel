from django import forms


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)

    def clean(self):
        self.before_clean()
        super(BaseForm, self).clean()
        if not self.errors:
            self.after_clean(self.cleaned_data)
        return self.cleaned_data

    def before_clean(self):
        pass

    def after_clean(self, cleaned_data):
        pass


class AddRegistrationKeyForm(BaseForm):

    expire = forms.DateTimeField(
        input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%d'],
        required=True,
        label='Expires',
        widget=forms.DateTimeInput(attrs={"placeholder": "2022-04-15"})
    )
    description = forms.CharField(
        max_length=100,
        required=True,
        label='Description',
        widget=forms.TextInput(attrs={
            'placeholder': 'reg key number 1'
        })
    )

    def init_fields(self):
        self.fields['expire'].initial = self.expire
        self.fields['description'].initial = self.description

    def after_clean(self, cleaned_data):
        cleaned_data['expire'] = int(cleaned_data['expire'].timestamp())

    def __init__(self, *args, **kwargs):
        self.expire = kwargs.pop('expire', '')
        self.description = kwargs.pop('description', '')
        super(AddRegistrationKeyForm, self).__init__(*args, **kwargs)
        self.init_fields()


class EnableRegistrationForm(BaseForm):

    ENABLE_CHOICES = (
        ('DISABLED', 'disabled'),
        ('LINK', 'link'),
        ('PUBLIC', 'public'),
    )
    registration = forms.ChoiceField(
        required=False,
        label='Registration',
        initial="disabled",
        choices=ENABLE_CHOICES
    )

    def __init__(self, *args, **kwargs):
        self.registration = kwargs.pop('registration', '')
        super(EnableRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['registration'].initial = self.registration
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
