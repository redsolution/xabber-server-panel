RESPONSE_EXCEPTION_MESSAGES = {
    'connection_error': 'Connection error. Please try later.',
    'request_error': 'Request error: {}',
    'client_error': 'Client error: {}',
    'bad_status_code': 'Bad API response: status code {}',
    'invalid_json': 'Bad API response: invalid JSON.',
}


class ResponseException(Exception):
    def __init__(self, *args, **kwargs):
        self.type = kwargs.get('type')
        self.detail = kwargs.get('detail', '')
        super.__init__(*args, **kwargs)

    def get_error_message(self):
        msg_format_str = RESPONSE_EXCEPTION_MESSAGES.get(self.type) or '{}'
        return msg_format_str.format(self.detail)
