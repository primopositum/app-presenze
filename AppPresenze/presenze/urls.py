from django.urls import include, path

from presenze import views


# -----------------------------------------------------------------------------
# Profilo, account e autenticazione
# -----------------------------------------------------------------------------
account_urlpatterns = [
    path("profile/",         views.user_profile,     name="profile"),    
    path("change-password/", views.change_password,  name="change-password"),
    path("delete-account/",  views.delete_account,   name="delete-account"),
    path("create-account/",  views.create_account,   name="create-account"),
    path("getToken/", views.get_token,   name="get-token"),
    path("login/",    views.api_login,   name="login"),
    path("refresh/",  views.api_refresh, name="refresh"),
    path("logout/",   views.api_logout,  name="logout"),
    path("users/",    views.users_list,  name="users-list"),
    path("saldo/<int:u_id>/", views.saldo_detail, name="saldo-detail"),
    path("signatures/", views.signature_create, name="signature-create"),
    path("showSignatures/", views.signature_latest, name="signature-latest"),
]


# -----------------------------------------------------------------------------
# Presenze / Time entries
# -----------------------------------------------------------------------------
time_entry_urlpatterns = [
    path("time-entries/",                        views.timeentry_create,                    name="timeentry-create"),
    path("time-entries/range-override/",         views.timeentry_create_range_override,     name="timeentry-create-range-override"),
    path("time-entries/from-month/",             views.time_entries_from_month_to_previous,  name="timeentries-from-month"),
    path("time-entries/<int:te_id>/validation/", views.timeentry_update_validation_level,    name="timeentry-update-validation"),
    path("time-entries/<int:te_id>/",            views.timeentry_detail,                    name="timeentry-detail"),
    path("time-entries/bulk-validate-month/",    views.timeentry_bulk_validate_month,        name="timeentry-bulk-validate-month"),
]


# -----------------------------------------------------------------------------
# PDF
# -----------------------------------------------------------------------------
pdf_urlpatterns = [
    path("pdf/",                 views.presenze_mese_scorso_pdf,  name="presenze-mese-scorso-pdf"),
    path("trasferte/pdf/",       views.trasferte_mese_scorso_pdf, name="trasferte-mese-scorso-pdf"),
    path("trasferte/Singlepdf/", views.trasferta_singola_pdf,     name="trasferte-singola-pdf"),
]


# -----------------------------------------------------------------------------
# Trasferte
# -----------------------------------------------------------------------------
trasferte_urlpatterns = [
    path("trasferte/",                       views.trasferta_list,             name="get-trasferte"),
    path("trasferte/create/",                views.trasferta_create,           name="post-trasferte"),
    path("trasferte/<int:t_id>/",            views.trasferta_update,           name="update-trasferte"),
    path("trasferte/<int:tr_id>/validation/",views.trasferte_validation_level, name="validation-trasferte"),
    path("trasferte/<int:t_id>/delete/",     views.trasferta_delete,           name="delete-trasferte"),
    path("trasferte/<int:u_id>/<str:data>/dossier/", views.trasferta_dossier,   name="trasferta-dossier"),
]


# -----------------------------------------------------------------------------
# Spese e scontrini
# -----------------------------------------------------------------------------
spese_urlpatterns = [
    path("spese/<int:s_id>/",               views.spesa_manage,            name="spesa-manage"),
    path("trasferte/<int:t_id>/spese/",     views.spesa_list_by_trasferta, name="spesa-list"),
    path("trasferte/<int:t_id>/spese/create/", views.spesa_manage,         name="spesa-create"),
    path("trasferte/<int:t_id>/scontrini/", views.scontrini_endpoint, name="scontrini-endpoint"),
    path("trasferte/<int:t_id>/scontrini/<str:filename>/", views.scontrino_get, name="scontrino-get"),
    path("trasferte/<int:t_id>/scontrini/<str:filename>/delete/", views.scontrino_delete, name="scontrino-delete"),
]


# -----------------------------------------------------------------------------
# Automobili
# -----------------------------------------------------------------------------
automobili_urlpatterns = [
    path("automobili/",                  views.AutomobileListCreateView.as_view(), name="automobili-list-create"),
    path("automobili/<int:pk>/",         views.AutomobileDetailView.as_view(),     name="automobili-detail"),
    path("automobili/<int:pk>/delete/",  views.AutomobileDeleteView.as_view(),     name="automobili-delete"),
    path("automobili/<int:pk>/patch/",   views.AutomobilePatchView.as_view(),      name="automobili-patch"),
    path("automobili/<int:auto_id>/PDFauto/", views.pdf_auto_upload,               name="automobili-pdfauto-upload"),
    path("automobili/<int:auto_id>/PDFauto/delete/", views.pdf_auto_delete,        name="automobili-pdfauto-delete"),
    path("automobili/PDFauto/by-date/", views.pdf_auto_current_month_list,         name="automobili-pdfauto-by-date"),
    path("automobili/PDFauto/mese-corrente/", views.pdf_auto_current_month_list,   name="automobili-pdfauto-current-month"),
]


# -----------------------------------------------------------------------------
# Utilities bar
# -----------------------------------------------------------------------------
utilities_urlpatterns = [
    path("utilitiesbar/", views.UtilitiesBarListView.as_view(), name="utilitiesbar-list"),
]


# -----------------------------------------------------------------------------
# Clienti e contratti commerciali
# -----------------------------------------------------------------------------
commercial_urlpatterns = [
    path("clienti/", views.ClienteListCreateView.as_view(), name="clienti-list-create"),
    path("clienti/<int:pk>/", views.ClienteDetailView.as_view(), name="clienti-detail"),
    path("contratti-clienti/", views.ContrattoClienteListCreateView.as_view(), name="contratti-clienti-list-create"),
    path("contratti-clienti/<int:pk>/", views.ContrattoClienteDetailView.as_view(), name="contratti-clienti-detail"),
    path("contratti-clienti/<int:pk>/pool-task/", views.ContrattoClientePoolTaskView.as_view(), name="contratti-clienti-pool-task"),
]


# -----------------------------------------------------------------------------
# Jira: configurazione e scope
# -----------------------------------------------------------------------------
jira_configuration_urlpatterns = [
    path("jira/credentials/", views.JiraCredentialsView.as_view(), name="jira-credentials"),
    path("jira/credentials/token/", views.JiraCredentialsTokenView.as_view(), name="jira-credentials-token"),
    path("jira/filters/", views.UpdateJiraFiltersView.as_view(), name="updateJiraFilters"),
]


# -----------------------------------------------------------------------------
# Jira: board, stati e worklog
# -----------------------------------------------------------------------------
jira_board_urlpatterns = [
    path("jira/search/", views.JiraProxyView.as_view(), name="jira-search"),
    path("jira/statuses/", views.JiraStatusesView.as_view(), name="jira-statuses"),
    path("jira/timesheet/", views.JiraWorklogsTodayView.as_view(), name="jira-timesheet"),
    path("jira/timesheet/month/", views.JiraWorklogsMonthView.as_view(), name="jira-timesheet-month"),
    path("jira/worklogs/user-monthly/", views.JiraUserMonthlyWorklogView.as_view(), name="jira-worklogs-user-monthly"),
    path("jira/worklogs/year/", views.JiraWorklogView.as_view(), name="jira-worklogs-year"),
    path("jira/worklogs/year/stream/", views.JiraWorklogStreamView.as_view(), name="jira-worklogs-year-stream"),
    path("jira/work/<str:work_key>/state/", views.JiraUpdateState.as_view(), name="jira-work-update-state"),
    path("jira/time/<str:issue_key>/", views.JiraIssueTimeView.as_view(), name="jira-issue-time"),
    path("jira/time/<str:issue_key>/log/", views.JiraIssueWorklogView.as_view(), name="jira-worklog-create"),
    path("jira/time/<str:issue_key>/log/<str:worklog_id>/", views.JiraIssueWorklogView.as_view(), name="jira-worklog-detail"),
]


api_urlpatterns = [
    *account_urlpatterns,
    *time_entry_urlpatterns,
    *pdf_urlpatterns,
    *trasferte_urlpatterns,
    *spese_urlpatterns,
    *automobili_urlpatterns,
    *utilities_urlpatterns,
    *commercial_urlpatterns,
    *jira_configuration_urlpatterns,
    *jira_board_urlpatterns,
]


urlpatterns = [
    path("api/", include(api_urlpatterns)),
]

