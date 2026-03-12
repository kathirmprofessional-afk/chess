from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-input w-full pl-11 py-3 bg-[#0f172a]/50 border-slate-700/50 focus:bg-[#0f172a] focus:border-purple-400/50 transition-all shadow-inner rounded-lg text-white',
        'placeholder': 'player@example.com',
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input w-full pl-11 py-3 bg-[#0f172a]/50 border-slate-700/50 focus:bg-[#0f172a] focus:border-purple-400/50 transition-all shadow-inner rounded-lg text-white',
            'placeholder': 'Choose a username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input w-full pl-11 py-3 bg-[#0f172a]/50 border-slate-700/50 focus:bg-[#0f172a] focus:border-purple-400/50 transition-all shadow-inner rounded-lg text-white',
            'placeholder': 'Create a password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input w-full pl-11 py-3 bg-[#0f172a]/50 border-slate-700/50 focus:bg-[#0f172a] focus:border-purple-400/50 transition-all shadow-inner rounded-lg text-white',
            'placeholder': 'Confirm your password',
        })
