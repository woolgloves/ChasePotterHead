from django.shortcuts import render, redirect
from django.db import connection
from django.views.decorators.csrf import csrf_exempt

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
