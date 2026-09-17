import socket
from urllib.parse import urlsplit, urlunsplit

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from ..models import UtilitiesBar
from ..serializer import UtilitiesBarSerializer


LOCALHOST_NAMES = {"localhost", "127.0.0.1", "::1"}


def _hostname_from_host_header(host_header):
    if not host_header:
        return None
    return urlsplit(f"//{host_header}").hostname


def _local_ip_for_request(request):
    request_host = _hostname_from_host_header(request.get_host())
    if request_host and request_host.lower() not in LOCALHOST_NAMES:
        return request_host

    remote_addr = request.META.get("REMOTE_ADDR")
    for target in (remote_addr, "8.8.8.8"):
        if not target or target in LOCALHOST_NAMES:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((target, 80))
                return sock.getsockname()[0]
        except OSError:
            continue

    return None

 
def _replace_localhost_link(link, server_ip):
    if not link or not server_ip:
        return link

    has_scheme = "://" in link
    parsed = urlsplit(link if has_scheme else f"//{link}")

    if not parsed.hostname or parsed.hostname.lower() not in LOCALHOST_NAMES:
        return link

    try:
        port = parsed.port
    except ValueError:
        return link

    host = f"[{server_ip}]" if ":" in server_ip and not server_ip.startswith("[") else server_ip
    netloc = f"{host}:{port}" if port else host
    rebuilt = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    return rebuilt if has_scheme else rebuilt.removeprefix("//")


class UtilitiesBarListView(ListAPIView):
    """
    GET /utilitiesbar/ -> lista ordinata per posizione.
    Endpoint in sola lettura: non espone POST/PUT/PATCH/DELETE.
    """

    serializer_class = UtilitiesBarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UtilitiesBar.objects.all().order_by("posizione", "id")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        server_ip = _local_ip_for_request(request)

        items = response.data
        if isinstance(items, dict) and "results" in items:
            items = items["results"]
        elif not isinstance(items, list):
            return response

        for item in items:
            item["link"] = _replace_localhost_link(item.get("link"), server_ip)

        return response
