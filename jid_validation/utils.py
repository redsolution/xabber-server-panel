import re

from jid import JID, parse


def validate_jid(value):
    try:
        jid_obj = JID(tuple=parse(value))
    except Exception as e:
        return {'success': False,
                'error_message': e}

    if jid_obj.user and jid_obj.host:
        return {"success": True,
                "full_jid": jid_obj.full().decode('ascii')}
    return {'success': False,
            'error_message': 'Invalid JID.'}
