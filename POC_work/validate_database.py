#!/usr/bin/env python3
"""
Comprehensive database validation script.
Checks all tables for data quality and completeness.
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "mtg_draft_coach.db"

def validate_card_data(set_code, test_card="invasion submersible"):
    """Validate card data, especially for the test card."""
    print("\n" + "=" * 80)
    print("CARD DATA VALIDATION")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Check test card
        print(f"\n[TEST CARD: {test_card.upper()}]")
        print("-" * 80)
        cursor.execute("""
            SELECT card_id, card_name, "set", color_identity, card_type, cmc, rarity
            FROM cards
            WHERE card_name = ?
        """, (test_card.lower(),))
        
        card_info = cursor.fetchone()
        if not card_info:
            print(f"  ERROR: Test card '{test_card}' not found!")
            return False
        
        card_id, name, set_code_db, color_identity, card_type, cmc, rarity = card_info
        print(f"  Card ID: {card_id}")
        print(f"  Set: {set_code_db}")
        print(f"  Color Identity: {color_identity or 'N/A'}")
        print(f"  Type: {card_type or 'N/A'}")
        print(f"  CMC: {cmc if cmc is not None else 'N/A'}")
        
        # Check card statistics
        cursor.execute("""
            SELECT gih_wr, gih_games, gih_wins, drawn_wr, drawn_games, drawn_wins,
                   overall_wr, total_games, total_wins
            FROM card_statistics
            WHERE card_id = ? AND "set" = ?
        """, (card_id, set_code))
        
        stats = cursor.fetchone()
        if not stats:
            print(f"  ERROR: No statistics found for test card!")
            return False
        
        gih_wr, gih_g, gih_w, drawn_wr, drawn_g, drawn_w, overall_wr, total_g, total_w = stats
        
        print(f"\n  Statistics:")
        print(f"    Opening Hand WR: {gih_wr:.3f if gih_wr is not None else 'N/A'} ({gih_w or 0} wins / {gih_g or 0} games)")
        print(f"    Drawn WR: {drawn_wr:.3f if drawn_wr is not None else 'N/A'} ({drawn_w or 0} wins / {drawn_g or 0} games)")
        print(f"    Overall WR: {overall_wr:.3f if overall_wr is not None else 'N/A'}")
        print(f"    Total Games: {total_g or 0:,}")
        
        # Validate win rates are not N/A
        issues = []
        if gih_wr is None and gih_g == 0:
            issues.append("Opening Hand Win Rate is N/A (no games in opening hand)")
        if drawn_wr is None and drawn_g == 0:
            issues.append("Drawn Win Rate is N/A (no games drawn)")
        if overall_wr is None:
            issues.append("Overall Win Rate is N/A")
        
        if issues:
            print(f"\n  WARNINGS:")
            for issue in issues:
                print(f"    - {issue}")
        
        # Check game_cards flags
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN in_opening_hand = 1 THEN 1 ELSE 0 END) as in_hand,
                SUM(CASE WHEN was_drawn = 1 THEN 1 ELSE 0 END) as drawn,
                SUM(CASE WHEN in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
        """, (card_id, set_code))
        
        gc_result = cursor.fetchone()
        total, in_hand, drawn, maindeck = gc_result
        print(f"\n  Game Cards Flags:")
        print(f"    Total records: {total:,}")
        print(f"    In opening hand: {in_hand:,}")
        print(f"    Was drawn: {drawn:,}")
        print(f"    In maindeck: {maindeck:,}")
        
        if in_hand == 0 and drawn == 0:
            print(f"  ERROR: No opening hand or drawn flags set!")
            return False
        
        # Overall card statistics summary
        print(f"\n[OVERALL CARD STATISTICS SUMMARY]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_cards,
                COUNT(CASE WHEN gih_wr IS NOT NULL THEN 1 END) as has_gih_wr,
                COUNT(CASE WHEN drawn_wr IS NOT NULL THEN 1 END) as has_drawn_wr,
                COUNT(CASE WHEN overall_wr IS NOT NULL THEN 1 END) as has_overall_wr,
                COUNT(CASE WHEN gih_games > 0 THEN 1 END) as cards_with_gih_games,
                COUNT(CASE WHEN drawn_games > 0 THEN 1 END) as cards_with_drawn_games
            FROM card_statistics
            WHERE "set" = ?
        """, (set_code,))
        
        summary = cursor.fetchone()
        total_cards, has_gih, has_drawn, has_overall, cards_gih, cards_drawn = summary
        print(f"  Total cards: {total_cards:,}")
        print(f"  Cards with GIH WR: {has_gih:,} ({has_gih/total_cards*100:.1f}%)")
        print(f"  Cards with Drawn WR: {has_drawn:,} ({has_drawn/total_cards*100:.1f}%)")
        print(f"  Cards with Overall WR: {has_overall:,} ({has_overall/total_cards*100:.1f}%)")
        print(f"  Cards with GIH games: {cards_gih:,}")
        print(f"  Cards with Drawn games: {cards_drawn:,}")
        
        if has_gih == 0 or has_drawn == 0:
            print(f"  ERROR: No cards have win rate data!")
            return False
        
        return True

def validate_archetype_table(set_code):
    """Validate archetype table data quality."""
    print("\n" + "=" * 80)
    print("ARCHETYPE TABLE VALIDATION")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Count archetypes
        cursor.execute("""
            SELECT COUNT(*) FROM color_archetypes WHERE "set" = ?
        """, (set_code,))
        total_archetypes = cursor.fetchone()[0]
        print(f"\n  Total archetypes: {total_archetypes:,}")
        
        if total_archetypes == 0:
            print(f"  ERROR: No archetypes found!")
            return False
        
        # Check data completeness
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN win_rate IS NOT NULL THEN 1 END) as has_wr,
                COUNT(CASE WHEN total_games > 0 THEN 1 END) as has_games,
                COUNT(CASE WHEN avg_num_turns IS NOT NULL THEN 1 END) as has_turns,
                COUNT(CASE WHEN on_play_win_rate IS NOT NULL THEN 1 END) as has_on_play,
                COUNT(CASE WHEN on_draw_win_rate IS NOT NULL THEN 1 END) as has_on_draw,
                COUNT(CASE WHEN avg_mulligans IS NOT NULL THEN 1 END) as has_mulligans
            FROM color_archetypes
            WHERE "set" = ?
        """, (set_code,))
        
        completeness = cursor.fetchone()
        total, has_wr, has_games, has_turns, has_on_play, has_on_draw, has_mulligans = completeness
        
        print(f"\n  Data Completeness:")
        print(f"    Total archetypes: {total:,}")
        print(f"    Has win rate: {has_wr:,} ({has_wr/total*100:.1f}%)")
        print(f"    Has games: {has_games:,} ({has_games/total*100:.1f}%)")
        print(f"    Has avg turns: {has_turns:,} ({has_turns/total*100:.1f}%)")
        print(f"    Has on-play WR: {has_on_play:,} ({has_on_play/total*100:.1f}%)")
        print(f"    Has on-draw WR: {has_on_draw:,} ({has_on_draw/total*100:.1f}%)")
        print(f"    Has avg mulligans: {has_mulligans:,} ({has_mulligans/total*100:.1f}%)")
        
        # Top archetypes by games
        print(f"\n  Top 10 Archetypes by Games:")
        cursor.execute("""
            SELECT main_colors, splash_colors, total_games, total_wins, win_rate,
                   avg_num_turns, on_play_win_rate, on_draw_win_rate
            FROM color_archetypes
            WHERE "set" = ? AND total_games > 0
            ORDER BY total_games DESC
            LIMIT 10
        """, (set_code,))
        
        top_archetypes = cursor.fetchall()
        if top_archetypes:
            print(f"    {'Colors':<20} {'Games':<10} {'Wins':<10} {'WR':<8} {'Turns':<8} {'On Play':<8} {'On Draw':<8}")
            print("    " + "-" * 80)
            for arch in top_archetypes:
                main, splash, games, wins, wr, turns, on_play, on_draw = arch
                colors = f"{main or ''}{splash or ''}"
                wr_str = f"{wr:.3f}" if wr is not None else "N/A"
                turns_str = f"{turns:.1f}" if turns is not None else "N/A"
                on_play_str = f"{on_play:.3f}" if on_play is not None else "N/A"
                on_draw_str = f"{on_draw:.3f}" if on_draw is not None else "N/A"
                print(f"    {colors:<20} {games:<10} {wins or 0:<10} {wr_str:<8} {turns_str:<8} {on_play_str:<8} {on_draw_str:<8}")
        else:
            print(f"    No archetypes with games found")
        
        # Check for issues
        issues = []
        if has_wr < total * 0.9:  # Less than 90% have win rates
            issues.append(f"Only {has_wr/total*100:.1f}% of archetypes have win rates")
        if has_games < total * 0.9:
            issues.append(f"Only {has_games/total*100:.1f}% of archetypes have games")
        
        if issues:
            print(f"\n  WARNINGS:")
            for issue in issues:
                print(f"    - {issue}")
        
        return True

def validate_draft_pick_table(set_code):
    """Validate draft pick table data quality."""
    print("\n" + "=" * 80)
    print("DRAFT PICK TABLE VALIDATION")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Count picks
        cursor.execute("""
            SELECT COUNT(*) FROM draft_picks WHERE "set" = ?
        """, (set_code,))
        total_picks = cursor.fetchone()[0]
        print(f"\n  Total draft picks: {total_picks:,}")
        
        if total_picks == 0:
            print(f"  ERROR: No draft picks found!")
            return False
        
        # Check data completeness
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT draft_id) as unique_drafts,
                COUNT(DISTINCT card_id) as unique_cards,
                COUNT(CASE WHEN pick_number IS NOT NULL THEN 1 END) as has_pick_num,
                COUNT(CASE WHEN pack_number IS NOT NULL THEN 1 END) as has_pack_num,
                COUNT(CASE WHEN maindeck_rate IS NOT NULL THEN 1 END) as has_maindeck,
                COUNT(CASE WHEN sideboard_rate IS NOT NULL THEN 1 END) as has_sideboard,
                COUNT(CASE WHEN rank IS NOT NULL AND rank != '' THEN 1 END) as has_rank,
                COUNT(CASE WHEN event_match_wins IS NOT NULL THEN 1 END) as has_wins,
                COUNT(CASE WHEN event_match_losses IS NOT NULL THEN 1 END) as has_losses
            FROM draft_picks
            WHERE "set" = ?
        """, (set_code,))
        
        completeness = cursor.fetchone()
        total, unique_drafts, unique_cards, has_pick, has_pack, has_maindeck, \
        has_sideboard, has_rank, has_wins, has_losses = completeness
        
        print(f"\n  Data Completeness:")
        print(f"    Total picks: {total:,}")
        print(f"    Unique drafts: {unique_drafts:,}")
        print(f"    Unique cards: {unique_cards:,}")
        print(f"    Has pick number: {has_pick:,} ({has_pick/total*100:.1f}%)")
        print(f"    Has pack number: {has_pack:,} ({has_pack/total*100:.1f}%)")
        print(f"    Has maindeck rate: {has_maindeck:,} ({has_maindeck/total*100:.1f}%)")
        print(f"    Has sideboard rate: {has_sideboard:,} ({has_sideboard/total*100:.1f}%)")
        print(f"    Has rank: {has_rank:,} ({has_rank/total*100:.1f}%)")
        print(f"    Has match wins: {has_wins:,} ({has_wins/total*100:.1f}%)")
        print(f"    Has match losses: {has_losses:,} ({has_losses/total*100:.1f}%)")
        
        # Pick distribution
        print(f"\n  Pick Number Distribution:")
        cursor.execute("""
            SELECT pick_number, COUNT(*) as cnt
            FROM draft_picks
            WHERE "set" = ? AND pick_number IS NOT NULL
            GROUP BY pick_number
            ORDER BY pick_number
            LIMIT 15
        """, (set_code,))
        
        pick_dist = cursor.fetchall()
        if pick_dist:
            print(f"    {'Pick':<8} {'Count':<10}")
            print("    " + "-" * 20)
            for pick_num, cnt in pick_dist:
                print(f"    {pick_num:<8} {cnt:,}")
        
        # Pack distribution
        print(f"\n  Pack Number Distribution:")
        cursor.execute("""
            SELECT pack_number, COUNT(*) as cnt
            FROM draft_picks
            WHERE "set" = ? AND pack_number IS NOT NULL
            GROUP BY pack_number
            ORDER BY pack_number
        """, (set_code,))
        
        pack_dist = cursor.fetchall()
        if pack_dist:
            print(f"    {'Pack':<8} {'Count':<10}")
            print("    " + "-" * 20)
            for pack_num, cnt in pack_dist:
                print(f"    {pack_num:<8} {cnt:,}")
        
        # Check for issues
        issues = []
        if has_pick < total * 0.9:
            issues.append(f"Only {has_pick/total*100:.1f}% of picks have pick numbers")
        if has_pack < total * 0.9:
            issues.append(f"Only {has_pack/total*100:.1f}% of picks have pack numbers")
        
        if issues:
            print(f"\n  WARNINGS:")
            for issue in issues:
                print(f"    - {issue}")
        
        return True

def validate_game_cards_table(set_code):
    """Validate game_cards table."""
    print("\n" + "=" * 80)
    print("GAME CARDS TABLE VALIDATION")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT game_id) as unique_games,
                COUNT(DISTINCT card_id) as unique_cards,
                SUM(CASE WHEN in_opening_hand = 1 THEN 1 ELSE 0 END) as in_hand,
                SUM(CASE WHEN was_drawn = 1 THEN 1 ELSE 0 END) as drawn,
                SUM(CASE WHEN in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck,
                SUM(CASE WHEN in_sideboard = 1 THEN 1 ELSE 0 END) as sideboard
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gr."set" = ?
        """, (set_code,))
        
        result = cursor.fetchone()
        total, unique_games, unique_cards, in_hand, drawn, maindeck, sideboard = result
        
        print(f"\n  Summary:")
        print(f"    Total records: {total:,}")
        print(f"    Unique games: {unique_games:,}")
        print(f"    Unique cards: {unique_cards:,}")
        print(f"    In opening hand: {in_hand:,}")
        print(f"    Was drawn: {drawn:,}")
        print(f"    In maindeck: {maindeck:,}")
        print(f"    In sideboard: {sideboard:,}")
        
        if in_hand == 0 and drawn == 0:
            print(f"\n  ERROR: No opening hand or drawn flags set!")
            return False
        
        return True

def main():
    """Run all validations."""
    if len(sys.argv) < 2:
        print("Usage: python validate_database.py <SET_CODE> [test_card_name]")
        print("Example: python validate_database.py TLA 'Invasion Submersible'")
        sys.exit(1)
    
    set_code = sys.argv[1].upper()
    test_card = sys.argv[2] if len(sys.argv) > 2 else "invasion submersible"
    
    print("=" * 80)
    print("DATABASE VALIDATION")
    print("=" * 80)
    print(f"Set: {set_code}")
    print(f"Database: {DB_PATH}")
    print(f"Test Card: {test_card}")
    
    results = {}
    
    # Run all validations
    results['card_data'] = validate_card_data(set_code, test_card)
    results['archetype'] = validate_archetype_table(set_code)
    results['draft_pick'] = validate_draft_pick_table(set_code)
    results['game_cards'] = validate_game_cards_table(set_code)
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("ALL VALIDATIONS PASSED!")
        return 0
    else:
        print("SOME VALIDATIONS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

