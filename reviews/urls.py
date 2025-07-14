# review/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('submit/<int:product_id>/', views.submit_review, name='submit_review'),
    path('vote/<int:review_id>/', views.vote_review, name='vote_review'),
    path('flag/<int:review_id>/', views.flag_review, name='flag_review'),
]
