Come generare il cronjob

1)  Dopo aver fatto "cd /path/alla/folder/del/progetto" (la cartella che contiene manage.py)
    Eseguire il seguente comando (senza virgolette):
    
    "path/al/python/del/venv/utilizzato manage.py NOME_COMANDO"

    dove "NOME_COMANDO" è il nome del file dove è scritto il command, senza l'estensione .py

2)  Creazione di una nuova entry di crontab
    Comando: "crontab -e"

3)  Scrivere il seguente testo (senza le virgolette) per indicare le specifiche del cronjob:
    "TZ=Europe/Rome 
    0 0 * * 1 cd /path/alla/folder/del/progetto && path/al/python/del/venv/utilizzato manage.py NOME_COMANDO >> /var/log/django_auto_timeentry.log 2>&1"

    Le righe attualmente presenti sono (senza virgolette):
    TZ=Europe/Rome 
    0 0 * * 1 cd /Workspace/Python/GestionalePresenzeTrasferte/AppPresenze && venv/bin/python manage.py genera_timeentries_settimana >> /var/log/django_auto_timeentry.log 2>&1

La dicitura "0 0 * * 1" indica lunedì alle 00:00
La dicitura ">> /var/log/django_auto_timeentry.log 2>&1" indica che l'output viene scritto nel file di log al path specificato
