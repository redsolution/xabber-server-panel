from jid_validation.utils import validate_jid
import random
import string


def get_system_group_suffix():
    return '_'.join(random.choice(string.ascii_lowercase) for i in range(8))
