from django import forms

from .models import UserProfile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["bio", "github_url", "linkedin_url", "avatar_url", "preferred_lang"]
