from django.urls import include, path
from presenze import views

api_urlpatterns = [
    # -------------------------------------------------------------------------
    # Profilo / Account
    # -------------------------------------------------------------------------
    path("profile/",         views.user_profile,     name="profile"),    
    path("change-password/", views.change_password,  name="change-password"),
    path("delete-account/",  views.delete_account,   name="delete-account"),

    # -------------------------------------------------------------------------
    # Auth JSON
    # -------------------------------------------------------------------------
    path("getToken/", views.get_token,   name="get-token"),
    path("login/",    views.api_login,   name="login"),
    path("logout/",   views.api_logout,  name="logout"),
    path("users/",    views.users_list,  name="users-list"),
    path("signatures/", views.signature_create, name="signature-create"),

    # -------------------------------------------------------------------------
    # Time Entries
    # -------------------------------------------------------------------------
    path("time-entries/",                        views.timeentry_create,                    name="timeentry-create"),
    path("time-entries/range-override/",         views.timeentry_create_range_override,     name="timeentry-create-range-override"),
    path("time-entries/from-month/",             views.time_entries_from_month_to_previous,  name="timeentries-from-month"),
    path("time-entries/<int:te_id>/validation/", views.timeentry_update_validation_level,    name="timeentry-update-validation"),
    path("time-entries/<int:te_id>/",            views.timeentry_detail,                    name="timeentry-detail"),
    path("time-entries/bulk-validate-month/",    views.timeentry_bulk_validate_month,        name="timeentry-bulk-validate-month"),

    # -------------------------------------------------------------------------
    # PDF
    # -------------------------------------------------------------------------
    path("pdf/",           views.presenze_mese_scorso_pdf,  name="presenze-mese-scorso-pdf"),
    path("trasferte/pdf/", views.trasferte_mese_scorso_pdf, name="trasferte-mese-scorso-pdf"),

    # -------------------------------------------------------------------------
    # Trasferte
    # -------------------------------------------------------------------------
    path("trasferte/",                       views.trasferta_list,             name="get-trasferte"),
    path("trasferte/create/",                views.trasferta_create,           name="post-trasferte"),
    path("trasferte/<int:t_id>/",            views.trasferta_update,           name="update-trasferte"),
    path("trasferte/<int:tr_id>/validation/",views.trasferte_validation_level, name="validation-trasferte"),
    path("trasferte/<int:t_id>/delete/",     views.trasferta_delete,           name="delete-trasferte"),
    path("trasferte/<int:u_id>/<str:data>/dossier/", views.trasferta_dossier,   name="trasferta-dossier"),

    # -------------------------------------------------------------------------
    # Spese
    # -------------------------------------------------------------------------
    path("spese/<int:s_id>/",               views.spesa_manage,            name="spesa-manage"),
    path("trasferte/<int:t_id>/spese/",     views.spesa_list_by_trasferta, name="spesa-list"),
    path("trasferte/<int:t_id>/spese/create/", views.spesa_manage,         name="spesa-create"),

    # -------------------------------------------------------------------------
    # Scontrini
    # -------------------------------------------------------------------------
    path("trasferte/<int:t_id>/scontrini/", views.scontrini_endpoint, name="scontrini-endpoint"),
    path("trasferte/<int:t_id>/scontrini/<str:filename>/", views.scontrino_get, name="scontrino-get"),
    path("trasferte/<int:t_id>/scontrini/<str:filename>/delete/", views.scontrino_delete, name="scontrino-delete"),

    # -------------------------------------------------------------------------
    # Automobili
    # -------------------------------------------------------------------------
    path("automobili/",                  views.AutomobileListCreateView.as_view(), name="automobili-list-create"),
    path("automobili/<int:pk>/",         views.AutomobileDetailView.as_view(),     name="automobili-detail"),
    path("automobili/<int:pk>/delete/",  views.AutomobileDeleteView.as_view(),     name="automobili-delete"),
    path("automobili/<int:pk>/patch/",   views.AutomobilePatchView.as_view(),      name="automobili-patch"),
    path("automobili/<int:auto_id>/PDFauto/", views.pdf_auto_upload,               name="automobili-pdfauto-upload"),
    path("automobili/PDFauto/mese-corrente/", views.pdf_auto_current_month_list,   name="automobili-pdfauto-current-month"),
]


urlpatterns = [
    path("api/", include(api_urlpatterns)),
]
