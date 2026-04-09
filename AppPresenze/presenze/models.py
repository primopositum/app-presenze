from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
import uuid


# ---------------------------
# Validatori utili
# ---------------------------

def validate_ore_sett_len_5(value):
    """Assicura che ore_sett abbia esattamente 5 elementi (lun-ven)."""
    if value is None:
        return
    if len(value) != 5:
        raise ValidationError("ore_sett deve contenere esattamente 5 valori (lun-ven).")


# ---------------------------
# Utente custom
# ---------------------------

class UtenteManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email è obbligatoria")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Il superuser deve avere is_superuser=True")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Il superuser deve avere is_staff=True")

        return self.create_user(email, password, **extra_fields)


class Utente(AbstractBaseUser, PermissionsMixin):
    """
    Tabella: Utente(U_ID, is_superuser, email, password_hash, nome, cognome, is_active, dati_anagrafici, data_creaz, data_upd)
    """

    id = models.BigAutoField(primary_key=True, db_column="U_ID")

    email = models.EmailField(unique=True)

    # Mappo il campo password Django (hash) sulla colonna password_hash
    password = models.CharField(max_length=128, db_column="password_hash")

    nome = models.CharField(max_length=75, blank=True)
    cognome = models.CharField(max_length=75, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    dati_anagrafici = models.JSONField(default=dict, blank=True)

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    objects = UtenteManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "Utente"

    def __str__(self):
        return self.email


# ---------------------------
# TimeEntry
# ---------------------------

class TimeEntry(models.Model):
    """
    TimeEntry(TE_ID, U_ID, type, ore_tot, data, validation_level, data_creaz, data_upd, note)
    """

    class EntryType(models.IntegerChoices):
        LAVORO_ORDINARIO = 1, "Lavoro ordinario"
        FERIE = 2, "Ferie"
        VERSAMENTO_BANCA_ORE = 3, "Versamento banca ore"
        PRELIEVO_BANCA_ORE = 4, "Prelievo banca ore"
        MALATTIA = 5, "Malattia"
        PERMESSO_ORDINARIO = 6, "Permesso ordinario"
        PERMESSO_STUDIO = 7, "Permesso studio"
        PERMESSO_104 = 8, "Permesso 104"
        PERMESSO_EX_FESTIVITA = 9, "Permesso ex festività"
        PERMESSO_ROL = 10, "Permesso R.O.L."
        CONGEDO_MAT_PAT = 11, "Congedo maternità/paternità"
        SCIOPERO = 12, "Sciopero"
        FESTIVITA = 13, "Festività"

    class ValidationLevel(models.IntegerChoices):
        AUTO = 0, "Compilato automaticamente"
        VALIDATO_UTENTE = 1, "Validato dall'utente"
        VALIDATO_ADMIN = 2, "Validato dall'amministratore"

    id = models.BigAutoField(primary_key=True, db_column="TE_ID")
    utente = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="time_entries",
        db_column="U_ID",
    )

    type = models.IntegerField(choices=EntryType.choices)
    ore_tot = models.DecimalField(max_digits=6, decimal_places=2)
    data = models.DateField()

    validation_level = models.IntegerField(
        choices=ValidationLevel.choices,
        default=ValidationLevel.AUTO,
    )

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "TimeEntry"
        indexes = [
            models.Index(fields=["utente", "data"]),
            models.Index(fields=["data", "type"]),
        ]
        # Questo vincolo serve per evitare che per qualche motivo vengano creati dei doppioni nei record
        constraints = [
            models.UniqueConstraint(fields=["utente", "data", "type"], name="uniq_timeentry_utente_data_type")
        ]
    note = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Note aggiuntive",
        help_text="Inserisci eventuali dettagli sulla trasferta"
    )
    def __str__(self):
        return f"{self.utente.email} - {self.data} ({self.get_type_display()}: {self.ore_tot}h)"


# ---------------------------
# Saldo
# ---------------------------

class Saldo(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="S_ID")
    utente = models.OneToOneField(  # uno-a-uno = 1 saldo per utente
        Utente,
        on_delete=models.CASCADE,
        related_name="saldo",
        db_column="U_ID",
    )

    valore_saldo_validato = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valore_saldo_sospeso = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Saldo"

# ---------------------------
# Contratto
# ---------------------------

class Contratto(models.Model):
    """
    Contratto(C_ID, U_ID, data_ass, data_fine, is_active, tipologia, ore_sett, data_creaz, data_upd)

    ore_sett: 5 valori (lun-ven)
    """

    id = models.BigAutoField(primary_key=True, db_column="C_ID")
    utente = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="contratti",
        db_column="U_ID",
    )

    data_ass = models.DateField()
    data_fine = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    tipologia = models.CharField(max_length=100)

    # Scelta consigliata: ArrayField perché è fisso a 5 elementi e resta “tipizzato”
    ore_sett = ArrayField(
        base_field=models.DecimalField(max_digits=5, decimal_places=2),
        size=5,
        default=list,
        validators=[validate_ore_sett_len_5],
        help_text="Ore nominali lun-ven, es: [8,8,8,8,8]",
    )

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Contratto"
        indexes = [
            models.Index(fields=["utente", "is_active"]),
        ]

    def __str__(self):
        return f"Contratto {self.utente.email} ({self.tipologia})"

    @property
    def ore_lun_ven(self):
        """Comodità: ritorna un dict lun->ven senza cambiare storage."""
        labels = ["lun", "mar", "mer", "gio", "ven"]
        if not self.ore_sett:
            return {k: None for k in labels}
        return dict(zip(labels, self.ore_sett))


# ---------------------------
# Automobile
# ---------------------------

class Automobile(models.Model):
    """
    Automobile(A_ID, marca, alimentazione, descrizione, is_active, coefficiente,
               data_creaz, data_upd)
    """

    id = models.BigAutoField(primary_key=True, db_column="A_ID")

    marca = models.CharField(max_length=100)
    alimentazione = models.CharField(max_length=50)
    descrizione = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    coefficiente = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Automobile"
        indexes = [
            models.Index(fields=["marca", "alimentazione"]),
        ]

    def __str__(self):
        return f"{self.marca} ({self.alimentazione})"


# ---------------------------
# Trasferta
# ---------------------------

class Trasferta(models.Model):
    """
    Trasferta(T_ID, U_ID, A_ID, data, azienda, indirizzo,
              data_creaz, data_upd, note, validation_level)
    """

    id = models.BigAutoField(primary_key=True, db_column="T_ID")
    utente = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="trasferte",
        db_column="U_ID",
    )

    automobile = models.ForeignKey(
        Automobile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trasferte",
        db_column="A_ID",
    )
    
    class ValidationLevel(models.IntegerChoices):
        VALIDATO_UTENTE = 1, "Validato dall'utente"
        VALIDATO_ADMIN = 2, "Validato dall'amministratore"

    data = models.DateField()
    azienda = models.CharField(max_length=255, blank=True)
    indirizzo = models.CharField(max_length=500, blank=True, null=True)
    validation_level = models.IntegerField(
        choices=ValidationLevel.choices,
        default=ValidationLevel.VALIDATO_UTENTE,
    )
    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)
    note = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Note aggiuntive",
        help_text="Inserisci eventuali dettagli sulla trasferta"
    )
    
    class Meta:
        db_table = "Trasferta"
        indexes = [
            models.Index(fields=["utente", "data"]),
            models.Index(fields=["data"]),
            models.Index(fields=["azienda"]),
        ]

    def __str__(self):
        return f"Trasferta {self.utente.email} - {self.data} - {self.azienda}"

    @property
    def totale_spese(self):
        if not self.pk:
            return 0
        totale = self.spese.aggregate(totale=models.Sum("importo"))["totale"]
        return totale or 0


# ---------------------------
# Spesa
# ---------------------------

class Spesa(models.Model):
    """
    Spesa(S_ID, T_ID, type, importo, data_creaz, data_upd)
    """

    class TrasfertaType(models.IntegerChoices):
        PEDAGGI = 1, "Pedaggi"
        KM = 2, "Rimborso km"
        RISTORANTI = 3, "Ristoranti"
        HOTEL = 4, "Albergo"
        PARCHEGGI = 5, "Parcheggi"
        BIGLIETTI = 6, "Aerei/treni"
        ALTRO = 7, "Altro"

    id = models.BigAutoField(primary_key=True, db_column="S_ID")

    trasferta = models.ForeignKey(
        Trasferta,
        on_delete=models.CASCADE,
        related_name="spese",
        db_column="T_ID",
    )

    type = models.IntegerField(choices=TrasfertaType.choices)
    importo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    data_creaz = models.DateTimeField(default=timezone.now)
    data_upd = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Spesa"
        indexes = [
            models.Index(fields=["trasferta"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"Spesa {self.type} - {self.importo}"


# ---------------------------
# Signature
# ---------------------------

class Signature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="signatures",
        db_column="U_ID",
    )
    svg = models.TextField(null=True, blank=True)
    image_data = models.BinaryField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, default="image/png")
    file_name = models.CharField(max_length=255, blank=True, default="")
    sha256 = models.CharField(max_length=64, db_index=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Signature"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="Signature_user_cr_70b9f5_idx"),
            models.Index(fields=["sha256"], name="Signature_sha256_5cb32b_idx"),
        ]


class SignatureEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        USED = "used", "Used"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(
        Signature,
        on_delete=models.CASCADE,
        related_name="events",
    )
    user = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="signature_events",
        db_column="U_ID",
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    document_id = models.UUIDField(null=True, blank=True)
    document_sha256 = models.CharField(max_length=64, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "SignatureEvent"
        indexes = [
            models.Index(fields=["signature", "-created_at"], name="SignatureEv_signat_8f2f97_idx"),
            models.Index(fields=["user", "-created_at"], name="SignatureEv_user_id_4c4f1c_idx"),
            models.Index(fields=["event_type", "-created_at"], name="SignatureEv_event_t_c75314_idx"),
        ]

