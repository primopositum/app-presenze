from django.contrib.auth import update_session_auth_hash
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import  Utente
from ..serializer import UtenteSerializer


def _is_staff_or_super(user):
    return user.is_staff or user.is_superuser

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")

    if not request.user.check_password(old_password):
        return Response({"error": "Vecchia password errata"}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)

    return Response({"message": "Password modificata con successo!"})

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    if request.method == 'GET':
        return Response(UtenteSerializer(request.user).data)

    serializer = UtenteSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(UtenteSerializer(request.user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def users_list(request):
    # if not _is_staff_or_super(request.user):
    #     return Response(
    #         {"errors": "Non hai i permessi per vedere questi utenti."},
    #         status=status.HTTP_403_FORBIDDEN,
    #     )

    qs = Utente.objects.all().order_by("email")
    serializer = UtenteSerializer(qs, many=True)
    return Response({
        "count": qs.count(),
        "results": serializer.data,
    })