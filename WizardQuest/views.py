
from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome to WizardQuest!")

    
    data = [
        {"id": r[0], "username": r[1], "level": r[2], "currency": r[3]}
        for r in rows
    ]
    return JsonResponse(data, safe=False)

