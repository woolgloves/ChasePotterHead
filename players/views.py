# WizardQuest/views.py
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password
from .forms import PlayerSignUpForm, PlayerLoginForm

def landing_page(request):
    return render(request, "landing.html")

def signup_view(request):
    if request.method == 'POST':
        form = PlayerSignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            hashed_password = make_password(password)
            level = 1
            currency = 100

            # Check duplicate username
            with connection.cursor() as cursor:
                cursor.execute("SELECT player_id FROM players WHERE username=%s", [username])
                if cursor.fetchone():
                    form.add_error('username', 'Username already exists.')
                    return render(request, 'signup.html', {'form': form})

                # Insert new player
                cursor.execute(
                    "INSERT INTO players (username, password, level, currency, house_id) VALUES (%s,%s,%s,%s,NULL)",
                    [username, hashed_password, level, currency]
                )
                new_player_id = cursor.lastrowid
                request.session['player_id'] = new_player_id
                request.session['username'] = username

            return redirect('landing')
    else:
        form = PlayerSignUpForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = PlayerLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            with connection.cursor() as cursor:
                cursor.execute("SELECT player_id, password FROM players WHERE username=%s", [username])
                row = cursor.fetchone()

            if row and check_password(password, row[1]):
                request.session['player_id'] = row[0]
                request.session['username'] = username
                return redirect('landing')

            error_message = 'Invalid username or password.'
    else:
        form = PlayerLoginForm()
    return render(request, 'login.html', {'form': form, 'error': error_message})
