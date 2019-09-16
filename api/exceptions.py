RESPONSE_EXCEPTION_MESSAGES = {
    'connection_error': 'Connection error. Please try later.',
    'request_error': 'Request error: {}',
    'client_error': 'Client error: {}',
    'bad_status_code': 'Bad API response: status code {}',
    'invalid_json': 'Bad API response: invalid JSON.',
}


class ResponseException(Exception):
    def get_error_message(self):
        data = self.message
        msg_type = data.get('type')
        msg_detail = data.get('detail') or ''
        msg_format_str = RESPONSE_EXCEPTION_MESSAGES.get(msg_type) or '{}'
        return msg_format_str.format(msg_detail)
