from django import forms

from .api import EjabberdAPI


ERRORS = {
    'You are not authorized to call this command.':
        'Wrong username or password. Access denied.'
}


class BaseApiForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.api_method = getattr(self.api, self.api_method)
        super(BaseApiForm, self).__init__(*args, **kwargs)

    def get_data_for_api(self):
        return self.cleaned_data

    def call_api(self):
        return self.api_method(self.get_data_for_api())

    def clean(self):
        self.before_clean()
        super(BaseApiForm, self).clean()
        if not self.errors:
            self.call_api()
            if not self.api.success:
                for field, error in self.api.response.items():
                    error = ERRORS.get(error) if ERRORS.get(error) else error
                    try:
                        self.add_error(field, error)
                    except ValueError:
                        self.add_error(None, error)
            else:
                self.after_clean(self.cleaned_data)
        return self.cleaned_data

    def before_clean(self):
        pass

    def after_clean(self, cleaned_data):
        pass


class ApiForm(BaseApiForm):
    def __init__(self, *args, **kwargs):
        self.api = EjabberdAPI()
        super(ApiForm, self).__init__(*args, **kwargs)


class AuthorizedApiForm(BaseApiForm):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.api = user.api
        super(AuthorizedApiForm, self).__init__(*args, **kwargs)
