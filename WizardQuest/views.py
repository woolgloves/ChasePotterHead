from django.shortcuts import render, redirect
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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



def xp_to_level_up(level):
    return 50 + level * 50  # Example: threshold per level

def battle_view(request, opponent_id):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('login')
    if player_id == opponent_id:
        return redirect('dashboard')

    with connection.cursor() as cursor:
        # Player info
        cursor.execute("""
            SELECT p.username, p.level, p.currency, p.house_id, p.experience, l.max_hp
            FROM players p
            JOIN level l ON p.level = l.level
            WHERE p.player_id=%s
        """, [player_id])
        player = cursor.fetchone()
        (player_name, player_level, player_currency, player_house,
         player_exp, player_max_hp) = player

        # Opponent info
        cursor.execute("""
            SELECT p.username, p.level, p.currency, p.house_id, l.max_hp
            FROM players p
            JOIN level l ON p.level = l.level
            WHERE p.player_id=%s
        """, [opponent_id])
        opponent = cursor.fetchone()
        (opponent_name, opponent_level, opponent_currency,
         opponent_house, opponent_max_hp) = opponent

    # Send to battle template
    context = {
        'player_id': player_id,
        'opponent_id': opponent_id,
        'player_name': player_name,
        'opponent_name': opponent_name,
        'player_max_hp': player_max_hp,
        'opponent_max_hp': opponent_max_hp,
        'player_hp': player_max_hp,   # Start at full HP
        'opponent_hp': opponent_max_hp,
        'player_level': player_level,
        'player_exp': player_exp,
        'player_currency': player_currency
    }

    return redirect('battle_result', battle_id=the_battle_id, winner_id=the_winner_id)


def battle_result_view(request, opponent_id, winner_id, exp_gain=0, currency_gain=0):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('login')

    with connection.cursor() as cursor:
        # Player info
        cursor.execute("""
            SELECT p.username, p.level, p.experience, p.currency, p.house_id
            FROM players p
            WHERE p.player_id=%s
        """, [player_id])
        player = cursor.fetchone()
        player_name, player_level, player_exp, player_currency, player_house = player

        # Opponent info
        cursor.execute("""
            SELECT p.username, p.level, p.house_id
            FROM players p
            WHERE p.player_id=%s
        """, [opponent_id])
        opponent = cursor.fetchone()
        opponent_name, opponent_level, opponent_house = opponent

        # Determine outcome
        if winner_id == player_id:
            outcome = 'You Won!'
        elif winner_id == opponent_id:
            outcome = f'{opponent_name} Won!'
        else:
            outcome = 'Draw'

        # Check level up
        new_level = player_level
        new_exp = player_exp + exp_gain
        while new_exp >= xp_to_level_up(new_level):
            new_exp -= xp_to_level_up(new_level)
            new_level += 1

        # Update player stats
        cursor.execute("""
            UPDATE players SET level=%s, experience=%s, currency=currency+%s
            WHERE player_id=%s
        """, [new_level, new_exp, currency_gain, player_id])

    context = {
        'player_name': player_name,
        'opponent_name': opponent_name,
        'outcome': outcome,
        'exp_gain': exp_gain,
        'currency_gain': currency_gain,
        'player_level': new_level,
        'player_exp': new_exp,
        'player_currency': player_currency + currency_gain
    }

    return render(request, 'WizardQuest/battle_result.html', context)