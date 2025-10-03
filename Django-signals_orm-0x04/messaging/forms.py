from django import forms
from .models import Message
from django.core.exceptions import ValidationError

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['receiver', 'content']
        widgets = {
            'receiver': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Start a new conversation...'
            }),
        }

class ReplyForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your reply...',
                'style': 'resize: vertical; min-height: 80px;'
            }),
        }

class MessageEditForm(forms.ModelForm):
    edit_reason = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Reason for editing (optional)',
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = Message
        fields = ['content', 'edit_reason']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
        }

class MessageEditForm(forms.ModelForm):
    edit_reason = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Reason for editing (optional)',
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = Message
        fields = ['content', 'edit_reason']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
        }

class UserDeleteForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password to confirm',
            'autocomplete': 'current-password',
        }),
        label="Your Password",
        help_text="Enter your current password to confirm account deletion"
    )
    
    confirmation = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type: DELETE MY ACCOUNT',
        }),
        label="Confirmation Phrase",
        help_text="Type 'DELETE MY ACCOUNT' exactly as shown to confirm"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if confirmation != 'DELETE MY ACCOUNT':
            raise ValidationError("Please type the confirmation phrase exactly as shown")
        return confirmation
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.user and not self.user.check_password(password):
            raise ValidationError("Invalid password")
        return password