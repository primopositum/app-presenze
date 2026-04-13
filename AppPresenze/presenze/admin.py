from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model
from .models import TimeEntry, Saldo, Contratto, Automobile, Trasferta, UtilitiesBar

admin.site.register(TimeEntry)
admin.site.register(Saldo)
admin.site.register(Automobile)
admin.site.register(Trasferta)
admin.site.register(UtilitiesBar)


User = get_user_model()

@admin.register(User)
class UtenteAdmin(DjangoUserAdmin):

    list_display = (
        "email",
        "nome",
        "cognome",
        "is_active",
        "is_staff",
        "is_superuser",
        "data_creaz",
    )

    # list_filter deve riferirsi a Fields reali (o filtri custom)
    list_filter = ("is_active", "is_staff", "is_superuser")

    search_fields = ("email",)
    ordering = ("email",)

    readonly_fields = ("data_creaz", "data_upd", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dati anagrafici (JSON)", {"fields": ("nome", "cognome")}),
        ("Permessi", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Date", {"fields": ("last_login", "data_creaz", "data_upd")}),
    )

    # Form di creazione utente in admin
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_active", "is_staff", "is_superuser"),
        }),
    )

@admin.register(Contratto)
class ContrattoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "utente",
        "tipologia",
        "data_ass",
        "data_fine",
        "is_active",
        "ore_sett_display",
    )
    list_display_links = ("id", "utente")

    list_filter = ("is_active", "utente", "tipologia")
    search_fields = ("utente__username", "tipologia")

    def ore_sett_display(self, obj):
        return ", ".join(str(int(o)) for o in obj.ore_sett)

    ore_sett_display.short_description = "Ore settimanali"

