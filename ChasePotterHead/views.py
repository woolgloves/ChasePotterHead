from django.shortcuts import render

def home(request):
    #return HttpResponse('HelloWorld! This is home page.')

    return render(request, 'website/index.html')


