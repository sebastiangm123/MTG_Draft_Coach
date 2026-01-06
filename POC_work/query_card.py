#!/usr/bin/env python3
"""
Query all data for a specific card.
Usage: python query_card.py "card name"
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "mtg_draft_coach.db"

def query_card(card_name):
    """Query all data for a card."""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Normalize card name (lowercase)
        card_name_lower = card_name.lower()
        
        print("=" * 80)
        print(f"ALL DATA FOR: {card_name}")
        print("=" * 80)
        print()
        
        # 1. Basic Card Information
        print("[BASIC CARD INFORMATION]")
        print("-" * 80)
        cursor.execute("""
            SELECT card_id, card_name, "set", color_identity, card_type, cmc, rarity
            FROM cards
            WHERE card_name = ?
        """, (card_name_lower,))
        
        card_info = cursor.fetchone()
        if not card_info:
            print(f"Card '{card_name}' not found in database.")
            print("\nSearching for similar card names...")
            cursor.execute("""
                SELECT card_name FROM cards
                WHERE card_name LIKE ?
                LIMIT 10
            """, (f"%{card_name_lower}%",))
            similar = cursor.fetchall()
            if similar:
                print("Similar cards found:")
                for row in similar:
                    print(f"  - {row[0]}")
            return
        
        card_id, name, set_code, color_identity, card_type, cmc, rarity = card_info
        print(f"  Card ID: {card_id}")
        print(f"  Name: {name}")
        print(f"  Set: {set_code}")
        print(f"  Color Identity: {color_identity or 'N/A'}")
        print(f"  Type: {card_type or 'N/A'}")
        print(f"  CMC: {cmc if cmc is not None else 'N/A'}")
        print(f"  Rarity: {rarity or 'N/A'}")
        print()
        
        # 2. Card Statistics
        print("[CARD STATISTICS]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                event_type,
                gih_wr, gih_games, gih_wins,
                drawn_wr, drawn_games, drawn_wins,
                overall_wr,
                ever_drawn_wr,
                maindeck_wr,
                avg_pick_number, avg_pack_number, total_picks,
                total_games, total_wins, total_losses,
                maindeck_rate, sideboard_rate
            FROM card_statistics
            WHERE card_id = ?
        """, (card_id,))
        
        stats = cursor.fetchall()
        if stats:
            for stat in stats:
                event_type, gih_wr, gih_g, gih_w, drawn_wr, drawn_g, drawn_w, overall_wr, \
                ever_drawn_wr, maindeck_wr, avg_pick, avg_pack, total_picks, \
                total_games, total_wins, total_losses, maindeck_rate, sideboard_rate = stat
                
                print(f"  Event Type: {event_type or 'N/A'}")
                gih_wr_str = f"{gih_wr:.3f}" if gih_wr is not None else "N/A"
                print(f"  Opening Hand Win Rate: {gih_wr_str} ({gih_w or 0} wins / {gih_g or 0} games)")
                drawn_wr_str = f"{drawn_wr:.3f}" if drawn_wr is not None else "N/A"
                print(f"  Drawn Win Rate: {drawn_wr_str} ({drawn_w or 0} wins / {drawn_g or 0} games)")
                overall_wr_str = f"{overall_wr:.3f}" if overall_wr is not None else "N/A"
                print(f"  Overall Win Rate: {overall_wr_str}")
                ever_drawn_wr_str = f"{ever_drawn_wr:.3f}" if ever_drawn_wr is not None else "N/A"
                print(f"  Ever Drawn Win Rate: {ever_drawn_wr_str}")
                maindeck_wr_str = f"{maindeck_wr:.3f}" if maindeck_wr is not None else "N/A"
                print(f"  Maindeck Win Rate: {maindeck_wr_str}")
                avg_pick_str = f"{avg_pick:.2f}" if avg_pick is not None else "N/A"
                print(f"  Average Pick Number: {avg_pick_str}")
                avg_pack_str = f"{avg_pack:.2f}" if avg_pack is not None else "N/A"
                print(f"  Average Pack Number: {avg_pack_str}")
                print(f"  Total Picks: {total_picks or 0:,}")
                print(f"  Total Games: {total_games or 0:,}")
                print(f"  Total Wins: {total_wins or 0:,}")
                print(f"  Total Losses: {total_losses or 0:,}")
                maindeck_rate_str = f"{maindeck_rate:.3f}" if maindeck_rate is not None else "N/A"
                print(f"  Maindeck Rate: {maindeck_rate_str}")
                sideboard_rate_str = f"{sideboard_rate:.3f}" if sideboard_rate is not None else "N/A"
                print(f"  Sideboard Rate: {sideboard_rate_str}")
                print()
        else:
            print("  No statistics found")
            print()
        
        # 3. Draft Pick Summary
        print("[DRAFT PICK SUMMARY]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_picks,
                COUNT(DISTINCT draft_id) as unique_drafts,
                AVG(pick_number) as avg_pick,
                AVG(pack_number) as avg_pack,
                AVG(maindeck_rate) as avg_maindeck_rate,
                MIN(pick_number) as earliest_pick,
                MAX(pick_number) as latest_pick
            FROM draft_picks
            WHERE card_id = ?
        """, (card_id,))
        
        pick_summary = cursor.fetchone()
        if pick_summary:
            total_picks, unique_drafts, avg_pick, avg_pack, avg_maindeck, earliest, latest = pick_summary
            print(f"  Total Picks: {total_picks:,}")
            print(f"  Unique Drafts: {unique_drafts:,}")
            avg_pick_str = f"{avg_pick:.2f}" if avg_pick is not None else "N/A"
            print(f"  Average Pick Number: {avg_pick_str}")
            avg_pack_str = f"{avg_pack:.2f}" if avg_pack is not None else "N/A"
            print(f"  Average Pack Number: {avg_pack_str}")
            avg_maindeck_str = f"{avg_maindeck:.3f}" if avg_maindeck is not None else "N/A"
            print(f"  Average Maindeck Rate: {avg_maindeck_str}")
            print(f"  Earliest Pick: {earliest if earliest is not None else 'N/A'}")
            print(f"  Latest Pick: {latest if latest is not None else 'N/A'}")
            print()
        
        # 4. Recent Draft Picks (sample)
        print("[RECENT DRAFT PICKS (Sample - Last 10)]")
        print("-" * 80)
        cursor.execute("""
            SELECT draft_id, draft_time, rank, pack_number, pick_number, 
                   maindeck_rate, event_match_wins, event_match_losses
            FROM draft_picks
            WHERE card_id = ?
            ORDER BY draft_time DESC
            LIMIT 10
        """, (card_id,))
        
        recent_picks = cursor.fetchall()
        if recent_picks:
            print(f"{'Draft ID':<20} {'Time':<20} {'Rank':<8} {'Pack':<6} {'Pick':<6} {'Maindeck':<10} {'W-L':<10}")
            print("-" * 80)
            for pick in recent_picks:
                draft_id, draft_time, rank, pack, pick_num, maindeck, wins, losses = pick
                wl = f"{wins}-{losses}" if wins is not None and losses is not None else "N/A"
                maindeck_str = f"{maindeck:.3f}" if maindeck is not None else "N/A"
                print(f"{str(draft_id)[:18]:<20} {str(draft_time)[:18]:<20} {str(rank or 'N/A'):<8} {pack or 'N/A':<6} {pick_num or 'N/A':<6} {maindeck_str:<10} {wl:<10}")
            print()
        else:
            print("  No draft picks found")
            print()
        
        # 5. Game Usage Summary
        print("[GAME USAGE SUMMARY]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT gc.game_id) as unique_games,
                SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as in_opening_hand,
                SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as was_drawn,
                SUM(CASE WHEN gc.in_maindeck = 1 THEN 1 ELSE 0 END) as in_maindeck,
                SUM(CASE WHEN gc.in_sideboard = 1 THEN 1 ELSE 0 END) as in_sideboard
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
        """, (card_id, set_code))
        
        game_usage = cursor.fetchone()
        if game_usage:
            total_rec, unique_games, in_hand, drawn, maindeck, sideboard = game_usage
            print(f"  Total Game Records: {total_rec:,}")
            print(f"  Unique Games: {unique_games:,}")
            print(f"  In Opening Hand: {in_hand:,}")
            print(f"  Was Drawn: {drawn:,}")
            print(f"  In Maindeck: {maindeck:,}")
            print(f"  In Sideboard: {sideboard:,}")
            print()
        
        # 6. Win Rate by Context
        print("[WIN RATE BY CONTEXT]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN gc.in_opening_hand = 1 AND gr.won = 1 THEN 1 ELSE 0 END) as hand_wins,
                SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as hand_games,
                SUM(CASE WHEN gc.was_drawn = 1 AND gr.won = 1 THEN 1 ELSE 0 END) as drawn_wins,
                SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as drawn_games,
                SUM(CASE WHEN gc.in_maindeck = 1 AND gr.won = 1 THEN 1 ELSE 0 END) as maindeck_wins,
                SUM(CASE WHEN gc.in_maindeck = 1 THEN 1 ELSE 0 END) as maindeck_games
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
        """, (card_id, set_code))
        
        win_rates = cursor.fetchone()
        if win_rates:
            hand_w, hand_g, drawn_w, drawn_g, maindeck_w, maindeck_g = win_rates
            if hand_g > 0:
                print(f"  Opening Hand WR: {hand_w}/{hand_g} = {hand_w/hand_g:.3f}")
            else:
                print(f"  Opening Hand WR: No data")
            
            if drawn_g > 0:
                print(f"  Drawn WR: {drawn_w}/{drawn_g} = {drawn_w/drawn_g:.3f}")
            else:
                print(f"  Drawn WR: No data")
            
            if maindeck_g > 0:
                print(f"  Maindeck WR: {maindeck_w}/{maindeck_g} = {maindeck_w/maindeck_g:.3f}")
            else:
                print(f"  Maindeck WR: No data")
            print()
        
        # 7. Color Combination Performance
        print("[PERFORMANCE BY COLOR COMBINATION]")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                gr.main_colors,
                COUNT(*) as games,
                SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ? AND gc.in_maindeck = 1
            GROUP BY gr.main_colors
            HAVING games >= 10
            ORDER BY win_rate DESC
            LIMIT 10
        """, (card_id, set_code))
        
        color_perf = cursor.fetchall()
        if color_perf:
            print(f"{'Colors':<15} {'Games':<10} {'Wins':<10} {'Win Rate':<10}")
            print("-" * 80)
            for row in color_perf:
                colors, games, wins, wr = row
                print(f"{str(colors or 'N/A'):<15} {games:<10} {wins:<10} {wr:.1f}%")
            print()
        else:
            print("  No color combination data (need 10+ games)")
            print()
        
        print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_card.py \"card name\"")
        print("Example: python query_card.py \"Invasion Submersible\"")
        sys.exit(1)
    
    card_name = sys.argv[1]
    query_card(card_name)

