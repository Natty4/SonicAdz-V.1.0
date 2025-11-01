from django import forms
from django.contrib.auth import get_user_model
from phonenumber_field.formfields import PhoneNumberField

User = get_user_model()

class UsersSignupForm(forms.Form):
    USER_TYPE_CHOICES = (
        ('advertiser', 'Advertiser'),
        ('creator', 'Creator'),
    )

    phone_number = PhoneNumberField(required=True)
    user_type = forms.CharField(widget=forms.HiddenInput())  

    def clean_user_type(self):
        user_type = self.cleaned_data.get('user_type')
        if user_type not in dict(self.USER_TYPE_CHOICES):
            raise forms.ValidationError('Invalid user type')
        return user_type

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("Invalide Phone number please try again with another phone number")
        return phone

    def signup(self, request, user):
        user.phone_number = self.cleaned_data['phone_number']
        user.user_type = self.cleaned_data['user_type']
        user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'address']
        read_only = ['email']