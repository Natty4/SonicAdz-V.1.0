from django.urls import path
from . import views

app_name = 'advertiser'

urlpatterns = [
    path('', views.advertiser_dashboard, name='dashboard'),
]