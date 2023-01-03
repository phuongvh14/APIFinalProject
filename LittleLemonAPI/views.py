from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def test(response):
    return HttpResponse("Hello Phuong")
