from django.shortcuts import render
from django.views.generic import CreateView,UpdateView,DeleteView,DetailView,ListView,TemplateView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .forms import UserRegistration
# Create your views here.
class signin(CreateView):
    model=User
    form_class=UserRegistration
    template_name='newlogin.html'
    success_url=reverse_lazy('mainpage')


class mainapge(TemplateView):
    template_name='mainpage.html'