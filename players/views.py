# WizardQuest/views.py
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password
from .forms import PlayerSignUpForm, PlayerLoginForm
import random



def signup_view(request):
    if request.method == 'POST':
        form = PlayerSignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            hashed_password = make_password(password)
            level = 1
            currency = 100
            with connection.cursor() as cursor:
                cursor.execute("SELECT house_id FROM house")
                houses = [row[0] for row in cursor.fetchall()]
            
            # 2. Randomly select a house
            house_id = random.choice(houses) if houses else None

            # Check duplicate username
            with connection.cursor() as cursor:
                cursor.execute("SELECT player_id FROM players WHERE username=%s", [username])
                if cursor.fetchone():
                    form.add_error('username', 'Username already exists.')
                    return render(request, 'signup.html', {'form': form})

                # Insert new player
                cursor.execute(
                    "INSERT INTO players (username, password, level, currency, house_id) VALUES (%s,%s,%s,%s,%s)",
                    [username, hashed_password, level, currency, house_id]
                )
                new_player_id = cursor.lastrowid
                request.session['player_id'] = new_player_id
                request.session['username'] = username

            return redirect('dashboard')
    else:
        form = PlayerSignUpForm()
    return render(request, 'players/signup.html', {'form': form})

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
                return redirect('dashboard')

            error_message = 'Invalid username or password.'
    else:
        form = PlayerLoginForm()
    return render(request, 'players/login.html', {'form': form, 'error': error_message})




def dashboard_view(request):
    # Check if player is logged in
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('login')

    data = {}

    with connection.cursor() as cursor:
        # 1. Player info
        cursor.execute("""
            SELECT username, level, currency, house_id
            FROM players
            WHERE player_id=%s
        """, [player_id])
        row = cursor.fetchone()
        if row:
            data['username'], data['level'], data['currency'], data['player_house_id'] = row

        # 2. All houses
        cursor.execute("SELECT house_id, house_name FROM house")
        data['houses'] = cursor.fetchall()

        # 3. Achievements for this player
        cursor.execute("""
            SELECT a.achievement_title, a.points_awarded, ia.awarded_at
            FROM achievements a
            JOIN is_awarded ia ON a.achievement_id = ia.achievement_id
            WHERE ia.player_id=%s
        """, [player_id])
        data['achievements'] = cursor.fetchall()

        # 4. Spells inventory
        cursor.execute("""
            SELECT s.name, s.damage, s.mana_cost
            FROM spells s
            JOIN is_learned_by il ON s.spell_id = il.spell_id
            WHERE il.player_id=%s
        """, [player_id])
        data['spells'] = cursor.fetchall()

        # 5. Players in other houses (for challenge)
        cursor.execute("""
            SELECT player_id, username, house_id
            FROM players
            WHERE player_id != %s
        """, [player_id])
        data['opponents'] = cursor.fetchall()

    return render(request, 'players/dashboard.html', data)

def logout_view(request):
    # Remove the player_id from the session
    if 'player_id' in request.session:
        del request.session['player_id']
    
    # Redirect to login page
    return redirect('player_login')