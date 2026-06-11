from django.urls import path,include
from .views import mainapge,signin
urlpatterns = [path('',mainapge.as_view(),name="main"),
               path("signin/",signin.as_view(),name="signin")]