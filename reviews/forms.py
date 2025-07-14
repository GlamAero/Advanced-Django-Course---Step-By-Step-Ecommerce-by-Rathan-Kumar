# reviews/forms.py
from django import forms
from .models import Review, ReviewFlag

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'images']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i}★") for i in range(1, 6)]),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review Title'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your review...'}),
        }

    images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'multiple': True,
            'class': 'form-control'
        })
    )

class ReviewFlagForm(forms.ModelForm):
    class Meta:
        model = ReviewFlag
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ReviewVoteForm(forms.Form):
    vote_type = forms.ChoiceField(choices=[('up', 'Helpful'), ('down', 'Not Helpful')])
