from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """Accetta header Authorization con prefisso Bearer invece di Token."""

    keyword = 'Bearer'

