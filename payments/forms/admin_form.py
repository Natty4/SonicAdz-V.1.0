from django import forms

class RejectPaymentMethodForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    rejection_reason = forms.CharField(
        label="Reason for Rejection (optional)",
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Leave blank to use a default rejection reason."
    )