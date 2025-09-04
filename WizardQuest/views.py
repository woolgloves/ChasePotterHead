from django.shortcuts import render, redirect
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import random

@csrf_exempt  # Allows POST requests without CSRF for now
def shop_view(request):
    # Check if player is logged in
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('login')

    message = None
    data = {}

    with connection.cursor() as cursor:
        # 1️⃣ Get player info (username and currency)
        cursor.execute("SELECT username, currency FROM players WHERE player_id=%s", [player_id])
        row = cursor.fetchone()
        if row:
            data['username'], data['currency'] = row
        else:
            return redirect('login')  # Just in case

        # 2️⃣ Get all spells
        cursor.execute("""
            SELECT spell_id, name, damage, mana_cost, price
            FROM spells
            ORDER BY spell_id
        """)
        all_spells = cursor.fetchall()

        # 3️⃣ Get spells already owned
        cursor.execute("SELECT spell_id FROM is_learned_by WHERE player_id=%s", [player_id])
        owned_spells = {row[0] for row in cursor.fetchall()}

        # 4️⃣ Handle buying a spell
        if request.method == "POST":
            spell_id_to_buy = int(request.POST.get("spell_id"))
            if spell_id_to_buy in owned_spells:
                message = "You already own this spell."
            else:
                # Get spell price
                cursor.execute("SELECT price FROM spells WHERE spell_id=%s", [spell_id_to_buy])
                price_row = cursor.fetchone()
                if price_row and data['currency'] >= price_row[0]:
                    # Deduct currency
                    cursor.execute(
                        "UPDATE players SET currency = currency - %s WHERE player_id=%s",
                        [price_row[0], player_id]
                    )
                    # Add spell to player's inventory
                    cursor.execute(
                        "INSERT INTO is_learned_by (player_id, spell_id) VALUES (%s, %s)",
                        [player_id, spell_id_to_buy]
                    )
                    data['currency'] -= price_row[0]
                    owned_spells.add(spell_id_to_buy)
                    message = "Spell purchased successfully!"
                else:
                    message = "Not enough currency."

        # 5️⃣ Prepare spells data for template
        data['spells'] = []
        for spell in all_spells:
            spell_id, name, damage, mana_cost, price = spell
            data['spells'].append({
                'id': spell_id,
                'name': name,
                'damage': damage,
                'mana_cost': mana_cost,
                'price': price,
                'owned': spell_id in owned_spells
            })

    data['message'] = message
    return render(request, 'WizardQuest/shop.html', data)



def challenge_player_view(request, opponent_id):
    """Creates a PENDING battle record when a player challenges another."""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

    with connection.cursor() as cursor:
        # Optional: Check if a challenge already exists between these players
        cursor.execute("""
            SELECT battle_id FROM battles WHERE 
            ((challenger_id = %s AND opponent_id = %s) OR (challenger_id = %s AND opponent_id = %s))
            AND status IN ('pending', 'active')
        """, [player_id, opponent_id, opponent_id, player_id])
        
        if cursor.fetchone():
            # A challenge already exists, so we don't create a new one.
            # You could add a Django message here to inform the user.
            return redirect('dashboard')

        # Create a new battle with 'pending' status. HP is set to 0 for now.
        # The opponent gets the first "turn" which is to accept or decline.
        cursor.execute("""
            INSERT INTO battles (status, challenger_id, opponent_id, challenger_hp, opponent_hp, current_turn_player_id)
            VALUES ('pending', %s, %s, 0, 0, %s)
        """, [player_id, opponent_id, opponent_id])

    return redirect('dashboard')

def respond_to_challenge_view(request, battle_id, action):
    """Handles the opponent's response (accept/decline) to a challenge."""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

    with connection.cursor() as cursor:
        if action == 'accept':
            # 1. Get player and opponent max HP to initialize the battle
            cursor.execute("SELECT challenger_id, opponent_id FROM battles WHERE battle_id = %s", [battle_id])
            challenger_id, opponent_id = cursor.fetchone()
            
            cursor.execute("SELECT l.max_hp FROM players p JOIN level l ON p.level=l.level WHERE p.player_id=%s", [challenger_id])
            challenger_max_hp = cursor.fetchone()[0]

            cursor.execute("SELECT l.max_hp FROM players p JOIN level l ON p.level=l.level WHERE p.player_id=%s", [opponent_id])
            opponent_max_hp = cursor.fetchone()[0]

            # 2. Update the battle: set status to 'active', set HP, and give the first turn to the challenger
            cursor.execute("""
                UPDATE battles SET status='active', challenger_hp=%s, opponent_hp=%s, current_turn_player_id=%s
                WHERE battle_id=%s AND opponent_id=%s
            """, [challenger_max_hp, opponent_max_hp, challenger_id, battle_id, player_id])
            
            # 3. Redirect to the battle page!
            return redirect('battle', battle_id=battle_id)
        
        elif action == 'decline':
            # If declined, simply delete the pending battle record.
            # We add 'opponent_id=%s' as a security check to ensure only the challenged player can decline.
            cursor.execute("DELETE FROM battles WHERE battle_id=%s AND opponent_id=%s AND status='pending'", [battle_id, player_id])
            return redirect('dashboard')

    return redirect('dashboard')

def get_player_data(cursor, player_id):
    """Helper function to fetch essential player data."""
    cursor.execute("""
        SELECT p.player_id, p.username, p.level, l.max_hp
        FROM players p JOIN level l ON p.level = l.level
        WHERE p.player_id = %s
    """, [player_id])
    row = cursor.fetchone()
    return {'id': row[0], 'username': row[1], 'level': row[2], 'max_hp': row[3]} if row else None

def battle_view(request, battle_id):
    """Handles displaying the battle state and processing a player's turn."""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

    with connection.cursor() as cursor:
        # Get the current, definitive state of the battle from the DB
        cursor.execute("""
            SELECT challenger_id, opponent_id, challenger_hp, opponent_hp, status, winner_id, current_turn_player_id 
            FROM battles WHERE battle_id = %s
        """, [battle_id])
        battle_row = cursor.fetchone()

        if not battle_row:
            return redirect('dashboard') # Battle doesn't exist

        challenger_id, opponent_id, challenger_hp, opponent_hp, status, winner_id, current_turn_player_id = battle_row
        
        # Security Check: Make sure the logged-in player is part of this battle
        if player_id not in [challenger_id, opponent_id]:
            return redirect('dashboard')

        # If the battle is already over, go straight to the results
        if status == 'finished':
            return redirect('battle_result', battle_id=battle_id)

        # --- Handle a POST request (a player making a move) ---
        if request.method == 'POST' and current_turn_player_id == player_id:
            spell_id = request.POST.get('spell_id')
            cursor.execute("SELECT damage FROM spells WHERE spell_id = %s", [spell_id])
            damage = cursor.fetchone()[0]

            # Determine who is attacking whom and update HP
            if player_id == challenger_id:
                opponent_hp -= damage
                next_turn_player_id = opponent_id
            else: # player_id is the opponent
                challenger_hp -= damage
                next_turn_player_id = challenger_id

            # Check for a winner
            if challenger_hp <= 0 or opponent_hp <= 0:
                challenger_hp = max(0, challenger_hp) # Prevent negative HP
                opponent_hp = max(0, opponent_hp)
                status = 'finished'
                winner_id = opponent_id if challenger_hp <= 0 else challenger_id
                
                cursor.execute("""
                    UPDATE battles SET challenger_hp=%s, opponent_hp=%s, status=%s, winner_id=%s WHERE battle_id=%s
                """, [challenger_hp, opponent_hp, status, winner_id, battle_id])
                
                return redirect('battle_result', battle_id=battle_id)
            else:
                # If no winner, update HP and flip the turn to the other player
                cursor.execute("""
                    UPDATE battles SET challenger_hp=%s, opponent_hp=%s, current_turn_player_id=%s WHERE battle_id=%s
                """, [challenger_hp, opponent_hp, next_turn_player_id, battle_id])
            
            # After processing the move, redirect to the same page to show the new state
            return redirect('battle', battle_id=battle_id)

        # --- Prepare data for displaying the page (GET request) ---
        challenger = get_player_data(cursor, challenger_id)
        opponent = get_player_data(cursor, opponent_id)
        
        # Get the current player's spells for the action panel
        cursor.execute("""
            SELECT s.spell_id, s.name, s.damage FROM spells s
            JOIN is_learned_by ilb ON s.spell_id = ilb.spell_id WHERE ilb.player_id = %s
        """, [player_id])
        player_spells = cursor.fetchall()
    
    context = {
        'battle_id': battle_id,
        'challenger': challenger,
        'opponent': opponent,
        'challenger_hp': challenger_hp,
        'opponent_hp': opponent_hp,
        'player_spells': player_spells,
        'is_my_turn': (current_turn_player_id == player_id),
        'player_id': player_id,
    }
    return render(request, 'WizardQuest/battle.html', context)

def battle_result_view(request, battle_id):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

    with connection.cursor() as cursor:
        # Get battle details: winner, challenger, and opponent IDs
        cursor.execute("SELECT winner_id, challenger_id, opponent_id FROM battles WHERE battle_id = %s", [battle_id])
        battle_info = cursor.fetchone()
        if not battle_info:
            return redirect('dashboard')
        winner_id, challenger_id, opponent_id = battle_info
        
        # Determine if the logged-in player is the winner
        is_winner = (winner_id == player_id)

        # Get the winner's current stats (level, xp, currency, house)
        cursor.execute("SELECT level, experience, currency, house_id FROM players WHERE player_id = %s", [winner_id])
        winner_stats = cursor.fetchone()
        winner_level, winner_exp, winner_currency, winner_house = winner_stats

        # Get the loser's house_id to compare
        loser_id = opponent_id if winner_id == challenger_id else challenger_id
        cursor.execute("SELECT house_id FROM players WHERE player_id = %s", [loser_id])
        loser_house = cursor.fetchone()[0]

        # --- REWARD CALCULATION LOGIC ---
        exp_gain = 0
        currency_gain = 0
        level_up = False

        if is_winner:
            # Base rewards for winning
            exp_gain = 50  # Base XP for a win
            
            # Check if houses are different
            if winner_house != loser_house:
                currency_gain = 25 # Currency reward for inter-house battle
        else:
            # Consolation prize for losing
            exp_gain = 10 
            currency_gain = 5

        # --- LEVEL UP LOGIC ---
        new_exp = winner_exp + exp_gain
        new_level = winner_level
        
        # Check if the player can level up, potentially multiple times
        while new_exp >= xp_for_next_level(new_level):
            level_up = True
            new_exp -= xp_for_next_level(new_level) # Subtract the threshold
            new_level += 1                          # Increment the level

        # --- UPDATE DATABASE FOR THE WINNER ---
        if is_winner:
            cursor.execute("""
                UPDATE players 
                SET level = %s, experience = %s, currency = currency + %s
                WHERE player_id = %s
            """, [new_level, new_exp, currency_gain, winner_id])
        
        # --- UPDATE DATABASE FOR THE LOSER (Optional, but good practice) ---
        else:
            # Just give the loser their consolation prize
            cursor.execute("""
                UPDATE players
                SET experience = experience + %s, currency = currency + %s
                WHERE player_id = %s
            """, [exp_gain, currency_gain, player_id])


        # Get winner and loser names for display
        cursor.execute("SELECT username FROM players WHERE player_id = %s", [winner_id])
        winner_name = cursor.fetchone()[0]
        
    context = {
        'outcome': f"{winner_name} is victorious!",
        'is_winner': is_winner,
        'exp_gain': exp_gain,
        'currency_gain': currency_gain,
        'level_up': level_up,
        'old_level': winner_level,
        'new_level': new_level,
    }
    return render(request, 'WizardQuest/battle_result.html', context)

def cancel_challenge_view(request, battle_id):
    """Allows a challenger to cancel a pending challenge they sent."""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('player_login')

    with connection.cursor() as cursor:
        # Delete the battle record, but only if the current player is the one who sent it.
        cursor.execute("DELETE FROM battles WHERE battle_id=%s AND challenger_id=%s AND status='pending'", [battle_id, player_id])
    
    return redirect('dashboard')

def xp_for_next_level(current_level):
    """Calculates the XP required to advance from the current level."""
    # This is a simple formula, you can make it more complex
    # e.g., 100 for level 1, 150 for level 2, 200 for level 3, etc.
    return 100 + (current_level * 10)