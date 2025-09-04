from django.db import connection
from django.contrib.auth.hashers import make_password, check_password

def create_player(username, raw_password, level=1, currency=100, house_id=None):
    hashed_pw = make_password(raw_password)
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO players (username, password, level, currency, house_id) VALUES (%s, %s, %s, %s, %s)",
            [username, hashed_pw, level, currency, house_id]
        )

def authenticate_player(username, raw_password):
    with connection.cursor() as cursor:
        cursor.execute("SELECT player_id, password FROM players WHERE username = %s", [username])
        row = cursor.fetchone()
        if row and check_password(raw_password, row[1]):
            return row[0]  # return player_id
    return None
