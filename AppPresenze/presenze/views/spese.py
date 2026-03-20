from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Trasferta, Spesa
from ..serializer import SpesaSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def spesa_list_by_trasferta(request, t_id: int):
    """
    GET /presenze/api/trasferte/<t_id>/spese/
    Lista tutte le spese associate a una specifica trasferta.
    """
    try:
        trasferta = Trasferta.objects.get(pk=t_id)
    except Trasferta.DoesNotExist:
        return Response(
            {"errors": "Trasferta non trovata."}, 
            status=status.HTTP_404_NOT_FOUND
        )
    is_super = request.user.is_superuser
    is_owner = (trasferta.utente_id == request.user.id)

    if not (is_super or is_owner):
        return Response(
            {"errors": "Non hai i permessi per visualizzare le spese di questa trasferta."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    spese = Spesa.objects.filter(trasferta_id=t_id).order_by('-data_creaz')
    serializer = SpesaSerializer(spese, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["POST", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def spesa_manage(request, t_id: int = None, s_id: int = None):
    """
    POST /presenze/api/trasferte/<t_id>/spese/ - Crea una nuova spesa
    PUT /presenze/api/spese/<s_id>/ - Modifica una spesa esistente
    DELETE /presenze/api/spese/<s_id>/ - Elimina una spesa
    
    Non è possibile creare/modificare/eliminare spese di trasferte validate dall'admin.
    """
    if request.method == "POST":
        if not t_id:
            return Response(
                {"errors": "ID trasferta richiesto per la creazione."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trasferta = Trasferta.objects.get(pk=t_id)
        except Trasferta.DoesNotExist:
            return Response(
                {"errors": "Trasferta non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile aggiungere spese a una trasferta validata dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per aggiungere spese a questa trasferta."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['trasferta'] = t_id
        
        serializer = SpesaSerializer(data=data)
        if serializer.is_valid():
            spesa = serializer.save()
            return Response(SpesaSerializer(spesa).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        if not s_id:
            return Response(
                {"errors": "ID spesa richiesto per la modifica."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spesa = Spesa.objects.select_related('trasferta', 'trasferta__utente').get(pk=s_id)
        except Spesa.DoesNotExist:
            return Response(
                {"errors": "Spesa non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if spesa.trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile modificare spese di trasferte validate dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (spesa.trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per modificare questa spesa."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        if 'trasferta' in data:
            del data['trasferta']
        
        serializer = SpesaSerializer(spesa, data=data, partial=True)
        if serializer.is_valid():
            spesa_aggiornata = serializer.save()
            return Response(SpesaSerializer(spesa_aggiornata).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if not s_id:
            return Response(
                {"errors": "ID spesa richiesto per l'eliminazione."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spesa = Spesa.objects.select_related('trasferta', 'trasferta__utente').get(pk=s_id)
        except Spesa.DoesNotExist:
            return Response(
                {"errors": "Spesa non trovata."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if spesa.trasferta.validation_level == Trasferta.ValidationLevel.VALIDATO_ADMIN:
            return Response(
                {"errors": "Non è possibile eliminare spese di trasferte validate dall'admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_super = request.user.is_superuser
        is_owner = (spesa.trasferta.utente_id == request.user.id)

        if not (is_super or is_owner):
            return Response(
                {"errors": "Non hai i permessi per eliminare questa spesa."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        spesa.delete()
        return Response(
            {"message": "Spesa eliminata con successo."}, 
            status=status.HTTP_204_NO_CONTENT
        )

