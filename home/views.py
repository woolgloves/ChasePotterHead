from django.shortcuts import render, HttpResponse

# Create your views here.
def index_page(request):
    return render(request,'home.html')

def login_page(request):
    return render(request, "login.html")

def signup_page(request):
    return render(request, "signup.html")