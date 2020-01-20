import re

from .jid import JID, parse


def validate_jid(value):
    try:
        jid_obj = JID(tuple=parse(value))
    except Exception as e:
        return {'success': False,
                'error_message': e}

    if jid_obj.user and jid_obj.host:
        try:
            full_jid = jid_obj.full().encode('ascii')
            return {"success": True, "full_jid": full_jid}
        except:
            pass

    return {'success': False,
            'error_message': 'Invalid JID.'}
