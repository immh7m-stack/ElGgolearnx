from django import forms
from allauth.account.forms import LoginForm, SignupForm

from .models import UserProfile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["bio", "github_url", "linkedin_url", "avatar_url", "preferred_lang"]


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "login" in self.fields:
            self.fields["login"].widget = forms.EmailInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-slate-100 outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/40",
                    "placeholder": "you@example.com",
                }
            )

        if "password" in self.fields:
            self.fields["password"].widget = forms.PasswordInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-slate-100 outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/40",
                    "placeholder": "••••••••",
                }
            )


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["username", "email", "password1", "password2"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update(
                    {
                        "class": "w-full rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-slate-100 outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/40",
                        "placeholder": self.fields[field_name].label,
                    }
                )
