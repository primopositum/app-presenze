from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    """
    Auth JWT che legge prima Authorization header (Bearer) e,
    in assenza, prova il cookie HttpOnly access_token.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        access_cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token")
        raw_token = request.COOKIES.get(access_cookie_name)
        if not raw_token:
            return None
        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception as exc:
            raise exceptions.AuthenticationFailed("Token cookie non valido") from exc
        return self.get_user(validated_token), validated_token

