from cryptography.fernet import InvalidToken
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django import forms
from .models import Secret
from .utils import encrypt, decrypt


class SecretCreateForm(forms.ModelForm):
    passphrase = forms.CharField(
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'placeholder': _('A word or phrase that\'s difficult to guess'),
        }),
        help_text=_("We don't store the passphrase."),
        error_messages={
            'required': _('Oops! Double check that passphrase'),
        })

    class Meta:
        model = Secret
        fields = ['data', 'passphrase', ]
        labels = {
            'data': _(''),
        }
        widgets = {
            'data': forms.Textarea(attrs={
                'cols': 100,
                'rows': 6,
                'placeholder': _('Secret content goes here...'),
            }),
        }
        error_messages = {
            'data': {
                'required': _('Oops! You did not provide anything to share'),
            }
        }

    def clean_data(self):
        max_size = 50 * 1024
        data = self.cleaned_data['data']
        size = len(bytes(data.encode('utf-8')))

        if size > max_size:
            raise forms.ValidationError(
                _('Oops! The maximum secret size is %(max)s') % {'max': filesizeformat(max_size)}
            )

        return data

    def save(self, force_insert=False, force_update=False, commit=True):
        passphrase = self.cleaned_data['passphrase']
        data = self.cleaned_data['data']

        instance = super(SecretCreateForm, self).save(commit=False)
        instance.data = encrypt(data, passphrase)

        if commit:
            instance.save()
        return instance


class SecretUpdateForm(forms.ModelForm):
    passphrase = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete':'off'}),
        label=_('Passphrase'),
        help_text=_('We will only show it once.'),
        error_messages={
            'required': _('Oops! Double check that passphrase'),
        })

    class Meta:
        model = Secret
        fields = ['passphrase', ]

    def clean_passphrase(self):
        passphrase = self.cleaned_data['passphrase']

        try:
            self.instance.decrypted_data = decrypt(self.instance.data, passphrase)
        except InvalidToken as e:
            raise forms.ValidationError(_('Oops! Double check that passphrase'))

        return passphrase
