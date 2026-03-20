from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Form personalizzato per la registrazione utenti."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'nome@esempio.com'
        }),
        label="Email"
    )
    
    nome = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        }),
        label="Nome"
    )
    
    cognome = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cognome'
        }),
        label="Cognome"
    )
    
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
    )
    
    password2 = forms.CharField(
        label="Conferma password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Conferma password'
        }),
        strip=False,
    )
    
    class Meta:
        model = User
        fields = ('email', 'nome', 'cognome', 'password1', 'password2')
    
    def save(self, commit=True):
        """Salva l'utente con i dati aggiuntivi."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.nome = self.cleaned_data["nome"]
        user.cognome = self.cleaned_data["cognome"]
        
        if commit:
            user.save()
        return user
    
class ProfileUpdateForm(forms.ModelForm):
    """Form per aggiornare i dati del profilo utente."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'nome@esempio.com'
        }),
        label="Email"
    )
    
    nome = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        }),
        label="Nome"
    )
    
    cognome = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cognome'
        }),
        label="Cognome"
    )
    
    class Meta:
        model = User
        fields = ('email', 'nome', 'cognome')
    
    def clean_email(self):
        """Verifica che l'email non sia già utilizzata da un altro utente."""
        email = self.cleaned_data['email']
        # Escludi l'utente corrente dal controllo
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Questa email è già utilizzata da un altro utente.")
        return email


class CustomPasswordChangeForm(PasswordChangeForm):
    """Form personalizzato per il cambio password."""
    
    old_password = forms.CharField(
        label="Password attuale",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password attuale'
        }),
    )
    
    new_password1 = forms.CharField(
        label="Nuova password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nuova password'
        }),
    )
    
    new_password2 = forms.CharField(
        label="Conferma nuova password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Conferma nuova password'
        }),
    )