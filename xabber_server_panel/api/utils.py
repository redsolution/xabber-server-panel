from .api import EjabberdAPI


def get_api(request):

    token = request.session.get('api_token')
    api = EjabberdAPI(request=request)

    if token:
        api.fetch_token(token)

    return api