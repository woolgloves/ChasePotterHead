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

def logout_view(request):
    # Remove the player_id from the session
    if 'player_id' in request.session:
        del request.session['player_id']
    
    # Redirect to login page
    return redirect('player_login')

def dashboard_view(request):
    # Check if player is logged in
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

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
        opponents = cursor.fetchall()

        # 6. Player cards (fetch battles challenged and wins)
        opponent_cards = []
        for opp in opponents:
            opp_id, opp_name, opp_house = opp

            # Total battles where this player was challenger or opponent
            cursor.execute("""
                SELECT COUNT(*) FROM battles
                WHERE challenger_id=%s OR opponent_id=%s
            """, [opp_id, opp_id])
            total_battles = cursor.fetchone()[0]

            # Total wins
            cursor.execute("""
                SELECT COUNT(*) FROM battles
                WHERE winner_id=%s
            """, [opp_id])
            total_wins = cursor.fetchone()[0]

            opponent_cards.append({
                'id': opp_id,
                'username': opp_name,
                'house_id': opp_house,
                'total_battles': total_battles,
                'wins': total_wins,
            })

        data['opponents'] = opponent_cards

        # 7. Get any INCOMING challenges for the current player (NEW CODE)
        # This finds battles where this player is the opponent and the status is 'pending'.
        cursor.execute("""
            SELECT b.battle_id, p.username 
            FROM battles b
            JOIN players p ON b.challenger_id = p.player_id
            WHERE b.opponent_id = %s AND b.status = 'pending'
        """, [player_id])
        data['incoming_challenges'] = cursor.fetchall()

        cursor.execute("""
            SELECT b.battle_id, p.username
            FROM battles b
            JOIN players p ON b.opponent_id = p.player_id
            WHERE b.challenger_id = %s AND b.status = 'pending'
        """, [player_id])
        data['outgoing_challenges'] = cursor.fetchall()

        # ====================================================================
        # NEW QUERY FOR ACTIVE BATTLES
        # ====================================================================
        # This finds battles where you are either the challenger or opponent AND the status is 'active'.
        cursor.execute("""
            SELECT b.battle_id, 
                   (SELECT username FROM players WHERE player_id = b.challenger_id),
                   (SELECT username FROM players WHERE player_id = b.opponent_id)
            FROM battles b
            WHERE (b.challenger_id = %s OR b.opponent_id = %s) AND b.status = 'active'
        """, [player_id, player_id])
        data['active_battles'] = cursor.fetchall()
        # ====================================================================

    # Fetch your opponent card data if needed (keeping your existing logic)
    # ... your existing logic for opponent_cards ...
    # data['opponents'] = opponent_cards
    

    return render(request, 'players/dashboard.html', data)