from rest_framework import serializers
from .models import Utente, TimeEntry, Saldo, Contratto, Trasferta, Spesa, Automobile
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

class UtenteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    saldo = serializers.SerializerMethodField()
    contratti = serializers.SerializerMethodField()

    class Meta:
        model = Utente
        fields = [
            'id',
            'is_superuser',
            'email',
            'password',
            'nome',
            'cognome',
            'is_active',
            'dati_anagrafici',
            'data_creaz',
            'data_upd',
            'saldo',
            'contratti'
        ]
        read_only_fields = ['data_creaz', 'data_upd', 'is_superuser']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Utente(**validated_data)
        if password:
            user.set_password(password)   # genera l'hash e lo salva in user.password
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
    def get_saldo(self, obj):
        try:
            saldo = obj.saldo  # OneToOne: singolo oggetto
        except ObjectDoesNotExist:
            return None
        return SaldoMiniSerializer(saldo).data
    
    def get_contratti(self, obj):
        qs = obj.contratti.order_by("-data_ass", "-id")
        return ContrattoMiniSerializer(qs, many=True).data


class TimeEntrySerializer(serializers.ModelSerializer):
    utente_id = serializers.IntegerField(write_only=True)
    utente = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "utente",
            "utente_id",
            "type",
            "ore_tot",
            "data",
            "note",
            "validation_level",
            "data_creaz",
            "data_upd",
        ]
        read_only_fields = ["id", "utente", "data_creaz", "data_upd"]

    @transaction.atomic
    def create(self, validated_data):
        utente_id = validated_data.pop("utente_id")
        entry_type = validated_data.get('type')
        ore_tot = validated_data.get('ore_tot')
        
        # Se è lavoro ordinario e supera le 8 ore, split automatico
        if entry_type == TimeEntry.EntryType.LAVORO_ORDINARIO and ore_tot > 8:
            ore_lavoro = Decimal('8.00')
            ore_banca = ore_tot - ore_lavoro
            
            # Crea entry lavoro ordinario (max 8 ore)
            validated_data['ore_tot'] = ore_lavoro
            validated_data["utente_id"] = utente_id
            time_entry = super().create(validated_data)
            
            # Crea entry versamento banca ore (ore eccedenti)
            TimeEntry.objects.create(
                utente_id=utente_id,
                data=validated_data['data'],
                type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                ore_tot=ore_banca,
                validation_level=validated_data.get('validation_level', TimeEntry.ValidationLevel.AUTO)
            )
            
            return time_entry
        
        # Comportamento normale
        validated_data["utente_id"] = utente_id
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        # utente_id non lo facciamo cambiare con PUT
        validated_data.pop("utente_id", None)
        
        # Gestiamo lo split solo se è lavoro ordinario
        entry_type = validated_data.get('type', instance.type)
        ore_tot = validated_data.get('ore_tot', instance.ore_tot)
        
        if entry_type == TimeEntry.EntryType.LAVORO_ORDINARIO:
            # Cerca se esiste già un'entry banca ore collegata
            banca_entry = TimeEntry.objects.filter(
                utente=instance.utente,
                data=validated_data.get('data', instance.data),
                type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE
            ).exclude(pk=instance.pk).first()
            
            if ore_tot > 8:
                # Caso: dobbiamo splittare (o aggiornare lo split esistente)
                ore_lavoro = Decimal('8.00')
                ore_banca = ore_tot - ore_lavoro
                
                validated_data['ore_tot'] = ore_lavoro
                instance = super().update(instance, validated_data)
                
                if banca_entry:
                    # Aggiorna l'entry banca ore esistente
                    banca_entry.ore_tot = ore_banca
                    banca_entry.validation_level = validated_data.get(
                        'validation_level', 
                        instance.validation_level
                    )
                    banca_entry.save()
                else:
                    # Crea nuova entry banca ore
                    TimeEntry.objects.create(
                        utente=instance.utente,
                        data=instance.data,
                        type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                        ore_tot=ore_banca,
                        validation_level=validated_data.get(
                            'validation_level',
                            instance.validation_level
                        )
                    )
                
                return instance
            
            else:
                # Caso: ore <= 8, eliminiamo l'entry banca ore se esiste
                if banca_entry:
                    banca_entry.delete()
                
                return super().update(instance, validated_data)
        
        # Se non è lavoro ordinario, comportamento normale
        return super().update(instance, validated_data)

class TrasfertaSerializer(serializers.ModelSerializer):
    utente_email = serializers.ReadOnlyField(source='utente.email')
    utente_nome = serializers.ReadOnlyField(source='utente.nome')
    utente_cognome = serializers.ReadOnlyField(source='utente.cognome')
    totale_spese = serializers.ReadOnlyField()

    class Meta:
        model = Trasferta
        fields = [
            'id', 'utente', 'utente_email', 'utente_nome', 'utente_cognome', 'automobile',
            'data', 'azienda', 'indirizzo', 
            'data_creaz', 'data_upd', 'note', 'totale_spese', 'validation_level'
        ]
        read_only_fields = ['id', 'data_creaz', 'data_upd', 'validation_level']


class TimeEntryValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ["validation_level"]

class SaldoMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Saldo
        fields = ("valore_saldo_validato", "valore_saldo_sospeso")

class ContrattoMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contratto
        # ore_sett è una lista di float
        fields = ("data_ass", "data_fine", "is_active", "tipologia", "ore_sett")

class SpesaSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    trasferta_data = serializers.DateField(source='trasferta.data', read_only=True)
    trasferta_azienda = serializers.CharField(source='trasferta.azienda', read_only=True)

    class Meta:
        model = Spesa
        fields = [
            'id', 'trasferta', 'trasferta_data', 'trasferta_azienda',
            'type', 'type_display', 'importo', 'data_creaz', 'data_upd'
        ]
        read_only_fields = ['id', 'data_creaz', 'data_upd']

    def validate_importo(self, value):
        if value < 0:
            raise serializers.ValidationError("L'importo non può essere negativo.")
        return value
    
class AutomobileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Automobile
        fields = "__all__"
        read_only_fields = ("id", "data_creaz", "data_upd")


class AutomobilePatchSerializer(serializers.ModelSerializer):
    """Serializer dedicato al PATCH dei campi consentiti su Automobile."""

    class Meta:
        model = Automobile
        fields = ("coefficiente", "is_active")

    def validate_coefficiente(self, value):
        if value < 0:
            raise serializers.ValidationError("Il coefficiente non può essere negativo.")
        return value
