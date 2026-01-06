#!/usr/bin/env python3
"""Diagnose why game_cards table has no opening_hand or drawn data."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "mtg_draft_coach.db"

with sqlite3.connect(str(DB_PATH)) as conn:
    cursor = conn.cursor()
    
    # Check a specific card
    cursor.execute("""
        SELECT card_id, card_name FROM cards 
        WHERE card_name = 'invasion submersible'
    """)
    card = cursor.fetchone()
    if card:
        card_id = card[0]
        print(f"Card ID: {card_id}, Name: {card[1]}")
        
        # Check game_cards records
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN in_opening_hand = 1 THEN 1 ELSE 0 END) as in_hand,
                SUM(CASE WHEN was_drawn = 1 THEN 1 ELSE 0 END) as drawn,
                SUM(CASE WHEN in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck,
                SUM(CASE WHEN in_sideboard = 1 THEN 1 ELSE 0 END) as sideboard
            FROM game_cards
            WHERE card_id = ?
        """, (card_id,))
        
        result = cursor.fetchone()
        print(f"\nGame Cards Records:")
        print(f"  Total: {result[0]:,}")
        print(f"  In Opening Hand: {result[1]:,}")
        print(f"  Was Drawn: {result[2]:,}")
        print(f"  In Maindeck: {result[3]:,}")
        print(f"  In Sideboard: {result[4]:,}")
        
        # Check a sample of records
        cursor.execute("""
            SELECT in_opening_hand, was_drawn, in_maindeck, in_sideboard
            FROM game_cards
            WHERE card_id = ?
            LIMIT 10
        """, (card_id,))
        
        print(f"\nSample records (first 10):")
        for row in cursor.fetchall():
            print(f"  OH={row[0]}, Drawn={row[1]}, Maindeck={row[2]}, Sideboard={row[3]}")

