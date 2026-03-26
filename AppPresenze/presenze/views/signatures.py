from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..serializer import SignatureSerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def signature_create(request):
    serializer = SignatureSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        signature = serializer.save()
        return Response(SignatureSerializer(signature).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
