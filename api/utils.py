import os

from django.core.exceptions import ValidationError

from django.conf import settings


# Used to save oauth token to session storage
def token_to_int(token):
    res = ''
    for char in token:
        char_code = str(ord(char))
        if len(char_code) == 1:
            char_code = '00' + char_code
        elif len(char_code) == 2:
            char_code = '0' + char_code
        res += char_code
    return int(res)


# Used to give user back
def int_to_token(number):
    hash_token = str(number)
    if len(hash_token) % 3 == 1:
        hash_token = '00' + hash_token
    elif len(hash_token) % 3 == 2:
        hash_token = '0' + hash_token

    token = ''
    while len(hash_token) != 0:
        char = chr(int(hash_token[:3]))
        token += char
        hash_token = hash_token[3:]
    return token


def file_size_validator(file_obj):
    if file_obj.size > settings.UPLOAD_IMG_MAX_SIZE:
        raise ValidationError(
            'File "%s" too large. Size should not exceed %s MB.' %
            (file_obj.name, settings.UPLOAD_IMG_MAX_SIZE / 1000000),
            code='invalid'
        )


def file_extension_validator(file_obj):
    file_extension = os.path.splitext(file_obj.name)[1]
    if file_extension not in [".gif", ".png", ".jpg", ".jpeg"]:
        raise ValidationError(
            'Invalid file format. Format should be GIF, PNG or JPG.',
            code='invalid'
        )
    return file_extension.split('.')[1]
