#!/usr/bin/env python3
"""
Comprehensive Card Data Query Tool
Shows all card, archetype, draft, and game data for a specific card.
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

def query_card_comprehensive(card_name, set_code, db_path="mtg_draft_coach.db"):
    """Query all data related to a specific card."""
    
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return False
    
    print("=" * 80)
    print(f"COMPREHENSIVE CARD DATA: {card_name.upper()}")
    print(f"Set: {set_code}")
    print("=" * 80)
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # ========================================================================
        # 1. CARD BASIC INFORMATION
        # ========================================================================
        print("\n" + "=" * 80)
        print("1. CARD BASIC INFORMATION")
        print("=" * 80)
        
        cursor.execute("""
            SELECT card_id, card_name, "set", color_identity, card_type, cmc, rarity
            FROM cards
            WHERE card_name = ? AND "set" = ?
        """, (card_name.lower(), set_code))
        
        card_info = cursor.fetchone()
        if not card_info:
            print(f"ERROR: Card '{card_name}' not found in set {set_code}")
            return False
        
        card_id, name, set_code_db, color_identity, card_type, cmc, rarity = card_info
        print(f"Card ID: {card_id}")
        print(f"Name: {name}")
        print(f"Set: {set_code_db}")
        print(f"Color Identity: {color_identity or 'Colorless'}")
        print(f"Type: {card_type or 'N/A'}")
        print(f"CMC: {cmc if cmc is not None else 'N/A'}")
        print(f"Rarity: {rarity or 'N/A'}")
        
        # ========================================================================
        # 2. CARD STATISTICS
        # ========================================================================
        print("\n" + "=" * 80)
        print("2. CARD PERFORMANCE STATISTICS")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                gih_wr, gih_games, gih_wins,
                drawn_wr, drawn_games, drawn_wins,
                overall_wr, ever_drawn_wr, maindeck_wr,
                avg_pick_number, avg_pack_number,
                total_picks, total_games, total_wins, total_losses,
                maindeck_rate, sideboard_rate
            FROM card_statistics
            WHERE card_id = ? AND "set" = ?
        """, (card_id, set_code))
        
        stats = cursor.fetchone()
        if stats:
            gih_wr, gih_games, gih_wins, drawn_wr, drawn_games, drawn_wins, \
            overall_wr, ever_drawn_wr, maindeck_wr, avg_pick, avg_pack, \
            total_picks, total_games, total_wins, total_losses, \
            maindeck_rate, sideboard_rate = stats
            
            print("\nWin Rate Metrics:")
            if gih_wr is not None:
                print(f"  Opening Hand Win Rate (GIH WR): {gih_wr:.4f} ({gih_wr*100:.2f}%)")
                print(f"    - Games in opening hand: {gih_games:,}")
                print(f"    - Wins when in opening hand: {gih_wins:,}")
            else:
                print(f"  Opening Hand Win Rate: N/A (no data)")
            
            if drawn_wr is not None:
                print(f"  Drawn Win Rate: {drawn_wr:.4f} ({drawn_wr*100:.2f}%)")
                print(f"    - Games where drawn: {drawn_games:,}")
                print(f"    - Wins when drawn: {drawn_wins:,}")
            else:
                print(f"  Drawn Win Rate: N/A (no data)")
            
            if overall_wr is not None:
                print(f"  Overall Win Rate: {overall_wr:.4f} ({overall_wr*100:.2f}%)")
            
            if ever_drawn_wr is not None:
                print(f"  Ever Drawn Win Rate: {ever_drawn_wr:.4f} ({ever_drawn_wr*100:.2f}%)")
            
            if maindeck_wr is not None:
                print(f"  Maindeck Win Rate: {maindeck_wr:.4f} ({maindeck_wr*100:.2f}%)")
            
            print("\nDraft Metrics:")
            print(f"  Total Picks: {total_picks:,}")
            if avg_pick is not None:
                print(f"  Average Pick Number: {avg_pick:.2f}")
            if avg_pack is not None:
                print(f"  Average Pack Number: {avg_pack:.2f}")
            
            print("\nUsage Metrics:")
            print(f"  Total Games: {total_games:,}")
            print(f"  Total Wins: {total_wins:,}")
            print(f"  Total Losses: {total_losses:,}")
            if total_games > 0:
                overall_record_wr = total_wins / total_games if total_wins else 0
                print(f"  Overall Record Win Rate: {overall_record_wr:.4f} ({overall_record_wr*100:.2f}%)")
            
            if maindeck_rate is not None:
                print(f"  Maindeck Rate: {maindeck_rate:.4f} ({maindeck_rate*100:.2f}%)")
            if sideboard_rate is not None:
                print(f"  Sideboard Rate: {sideboard_rate:.4f} ({sideboard_rate*100:.2f}%)")
        else:
            print("  No statistics found")
        
        # ========================================================================
        # 3. ARCHETYPE PERFORMANCE (Where this card was used)
        # ========================================================================
        print("\n" + "=" * 80)
        print("3. ARCHETYPE PERFORMANCE (Color Combinations Using This Card)")
        print("=" * 80)
        
        cursor.execute("""
            SELECT DISTINCT
                ca.main_colors,
                ca.splash_colors,
                ca.win_rate as archetype_wr,
                ca.total_games as archetype_games,
                COUNT(DISTINCT ds.draft_id) as drafts_with_card,
                AVG(ds.win_rate) as avg_draft_wr_with_card
            FROM color_archetypes ca
            JOIN draft_summaries ds ON ca.main_colors = ds.final_colors 
                AND (ca.splash_colors = ds.splash_colors OR (ca.splash_colors IS NULL AND ds.splash_colors IS NULL))
            JOIN draft_picks dp ON ds.draft_id = dp.draft_id
            WHERE dp.card_id = ? 
                AND ca."set" = ?
                AND ds."set" = ?
            GROUP BY ca.main_colors, ca.splash_colors, ca.win_rate, ca.total_games
            ORDER BY ca.win_rate DESC
            LIMIT 20
        """, (card_id, set_code, set_code))
        
        archetypes = cursor.fetchall()
        if archetypes:
            print(f"\nFound {len(archetypes)} archetypes using this card:\n")
            print(f"{'Archetype':<15} {'Splash':<10} {'Archetype WR':<15} {'Games':<12} {'Drafts':<10} {'Avg Draft WR':<15}")
            print("-" * 80)
            for arch in archetypes:
                main_colors, splash_colors, arch_wr, arch_games, drafts_count, avg_draft_wr = arch
                splash_str = splash_colors or "None"
                arch_wr_str = f"{arch_wr:.4f}" if arch_wr else "N/A"
                avg_draft_wr_str = f"{avg_draft_wr:.4f}" if avg_draft_wr else "N/A"
                print(f"{main_colors:<15} {splash_str:<10} {arch_wr_str:<15} {arch_games:<12,} {drafts_count:<10,} {avg_draft_wr_str:<15}")
        else:
            print("  No archetype data found")
        
        # ========================================================================
        # 4. DRAFT PICK DATA
        # ========================================================================
        print("\n" + "=" * 80)
        print("4. DRAFT PICK DATA")
        print("=" * 80)
        
        # Summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_picks,
                COUNT(DISTINCT draft_id) as unique_drafts,
                AVG(pack_number) as avg_pack,
                AVG(pick_number) as avg_pick,
                MIN(pick_number) as earliest_pick,
                MAX(pick_number) as latest_pick,
                AVG(maindeck_rate) as avg_maindeck_rate
            FROM draft_picks
            WHERE card_id = ? AND "set" = ?
        """, (card_id, set_code))
        
        pick_summary = cursor.fetchone()
        if pick_summary:
            total_picks, unique_drafts, avg_pack, avg_pick, earliest, latest, avg_maindeck = pick_summary
            print(f"\nSummary:")
            print(f"  Total Picks: {total_picks:,}")
            print(f"  Unique Drafts: {unique_drafts:,}")
            if avg_pack is not None:
                print(f"  Average Pack: {avg_pack:.2f}")
            if avg_pick is not None:
                print(f"  Average Pick: {avg_pick:.2f}")
            if earliest is not None:
                print(f"  Earliest Pick: {earliest}")
            if latest is not None:
                print(f"  Latest Pick: {latest}")
            if avg_maindeck is not None:
                print(f"  Average Maindeck Rate: {avg_maindeck:.4f} ({avg_maindeck*100:.2f}%)")
        
        # Pick distribution by pack
        cursor.execute("""
            SELECT 
                pack_number,
                COUNT(*) as pick_count,
                AVG(pick_number) as avg_pick_in_pack,
                AVG(maindeck_rate) as avg_maindeck_rate
            FROM draft_picks
            WHERE card_id = ? AND "set" = ?
            GROUP BY pack_number
            ORDER BY pack_number
        """, (card_id, set_code))
        
        pack_dist = cursor.fetchall()
        if pack_dist:
            print(f"\nPick Distribution by Pack:")
            print(f"{'Pack':<8} {'Picks':<12} {'Avg Pick #':<15} {'Maindeck Rate':<15}")
            print("-" * 50)
            for pack_num, count, avg_pick_pack, maindeck_rate in pack_dist:
                avg_pick_str = f"{avg_pick_pack:.2f}" if avg_pick_pack else "N/A"
                maindeck_str = f"{maindeck_rate:.4f}" if maindeck_rate else "N/A"
                print(f"{pack_num:<8} {count:<12,} {avg_pick_str:<15} {maindeck_str:<15}")
        
        # Sample recent picks
        cursor.execute("""
            SELECT 
                draft_id,
                pack_number,
                pick_number,
                maindeck_rate,
                draft_time
            FROM draft_picks
            WHERE card_id = ? AND "set" = ?
            ORDER BY draft_time DESC
            LIMIT 10
        """, (card_id, set_code))
        
        recent_picks = cursor.fetchall()
        if recent_picks:
            print(f"\nSample Recent Picks (last 10):")
            print(f"{'Draft ID':<40} {'Pack':<8} {'Pick':<8} {'Maindeck Rate':<15}")
            print("-" * 75)
            for draft_id, pack, pick, maindeck, draft_time in recent_picks:
                maindeck_str = f"{maindeck:.4f}" if maindeck else "N/A"
                draft_id_short = draft_id[:37] + "..." if len(draft_id) > 40 else draft_id
                print(f"{draft_id_short:<40} {pack:<8} {pick:<8} {maindeck_str:<15}")
        
        # ========================================================================
        # 5. GAME DATA
        # ========================================================================
        print("\n" + "=" * 80)
        print("5. GAME DATA")
        print("=" * 80)
        
        # Game presence summary
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT gc.game_id) as games_with_card,
                SUM(CASE WHEN gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as in_opening_hand,
                SUM(CASE WHEN gc.was_drawn = 1 THEN 1 ELSE 0 END) as was_drawn,
                SUM(CASE WHEN gc.in_maindeck = 1 THEN 1 ELSE 0 END) as in_maindeck,
                SUM(CASE WHEN gr.won = 1 AND gc.in_opening_hand = 1 THEN 1 ELSE 0 END) as wins_in_hand,
                SUM(CASE WHEN gr.won = 1 AND gc.was_drawn = 1 THEN 1 ELSE 0 END) as wins_when_drawn
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
        """, (card_id, set_code))
        
        game_summary = cursor.fetchone()
        if game_summary:
            games_with_card, in_hand, drawn, maindeck, wins_in_hand, wins_when_drawn = game_summary
            print(f"\nGame Presence Summary:")
            print(f"  Total Games with Card: {games_with_card:,}")
            print(f"  In Opening Hand: {in_hand:,}")
            print(f"  Was Drawn: {drawn:,}")
            print(f"  In Maindeck: {maindeck:,}")
            if in_hand > 0:
                hand_wr = wins_in_hand / in_hand
                print(f"  Win Rate in Opening Hand: {hand_wr:.4f} ({hand_wr*100:.2f}%)")
            if drawn > 0:
                drawn_wr = wins_when_drawn / drawn
                print(f"  Win Rate When Drawn: {drawn_wr:.4f} ({drawn_wr*100:.2f}%)")
        
        # Performance by archetype in games
        cursor.execute("""
            SELECT 
                gr.main_colors,
                COUNT(*) as games,
                SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as wins,
                AVG(gr.num_turns) as avg_turns
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ? AND gc.in_maindeck = 1
            GROUP BY gr.main_colors
            ORDER BY games DESC
            LIMIT 10
        """, (card_id, set_code))
        
        archetype_games = cursor.fetchall()
        if archetype_games:
            print(f"\nPerformance by Archetype in Games:")
            print(f"{'Archetype':<15} {'Games':<12} {'Wins':<10} {'Win Rate':<12} {'Avg Turns':<12}")
            print("-" * 65)
            for arch_colors, games, wins, avg_turns in archetype_games:
                wr = wins / games if games > 0 else 0
                avg_turns_str = f"{avg_turns:.2f}" if avg_turns else "N/A"
                print(f"{arch_colors:<15} {games:<12,} {wins:<10,} {wr:.4f} ({wr*100:.2f}%) {avg_turns_str:<12}")
        
        # Sample game results
        cursor.execute("""
            SELECT 
                gr.game_id,
                gr.draft_id,
                gr.won,
                gr.num_turns,
                gr.main_colors,
                gr.opp_colors,
                gc.in_opening_hand,
                gc.was_drawn
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
            ORDER BY gr.game_time DESC
            LIMIT 10
        """, (card_id, set_code))
        
        sample_games = cursor.fetchall()
        if sample_games:
            print(f"\nSample Recent Games (last 10):")
            print(f"{'Game ID':<12} {'Won':<6} {'Turns':<8} {'Colors':<10} {'Opp':<10} {'In Hand':<10} {'Drawn':<8}")
            print("-" * 75)
            for game_id, draft_id, won, turns, colors, opp, in_hand, drawn in sample_games:
                won_str = "Yes" if won else "No"
                in_hand_str = "Yes" if in_hand else "No"
                drawn_str = "Yes" if drawn else "No"
                turns_str = str(turns) if turns else "N/A"
                colors_str = colors or "N/A"
                opp_str = opp or "N/A"
                print(f"{game_id:<12} {won_str:<6} {turns_str:<8} {colors_str:<10} {opp_str:<10} {in_hand_str:<10} {drawn_str:<8}")
        
        # ========================================================================
        # 6. SUMMARY STATISTICS
        # ========================================================================
        print("\n" + "=" * 80)
        print("6. SUMMARY STATISTICS")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT dp.draft_id) as total_drafts,
                COUNT(DISTINCT gr.game_id) as total_games,
                COUNT(DISTINCT gr.main_colors) as unique_archetypes,
                AVG(gr.won) as overall_game_win_rate
            FROM draft_picks dp
            LEFT JOIN game_results gr ON dp.draft_id = gr.draft_id
            LEFT JOIN game_cards gc ON gr.game_id = gc.game_id AND gc.card_id = ?
            WHERE dp.card_id = ? AND dp."set" = ?
        """, (card_id, card_id, set_code))
        
        summary = cursor.fetchone()
        if summary:
            total_drafts, total_games, unique_archs, overall_wr = summary
            print(f"\nOverall Summary:")
            print(f"  Drafts with this card: {total_drafts:,}")
            print(f"  Games with this card: {total_games:,}")
            print(f"  Unique archetypes used in: {unique_archs:,}")
            if overall_wr is not None:
                print(f"  Overall game win rate: {overall_wr:.4f} ({overall_wr*100:.2f}%)")
        
        # ========================================================================
        # 7. EXPORT TO CSV
        # ========================================================================
        print("\n" + "=" * 80)
        print("7. EXPORTING DATA TO CSV")
        print("=" * 80)
        
        output_dir = Path("validation_outputs")
        output_dir.mkdir(exist_ok=True)
        
        # Export card statistics
        card_stats_df = pd.read_sql_query("""
            SELECT * FROM card_statistics
            WHERE card_id = ? AND "set" = ?
        """, conn, params=(card_id, set_code))
        if not card_stats_df.empty:
            filename = output_dir / f"card_{card_name.lower().replace(' ', '_')}_{set_code}_statistics.csv"
            card_stats_df.to_csv(filename, index=False)
            print(f"  Exported card statistics to: {filename}")
        
        # Export draft picks sample
        draft_picks_df = pd.read_sql_query("""
            SELECT 
                draft_id, pack_number, pick_number, maindeck_rate, draft_time
            FROM draft_picks
            WHERE card_id = ? AND "set" = ?
            ORDER BY draft_time DESC
            LIMIT 1000
        """, conn, params=(card_id, set_code))
        if not draft_picks_df.empty:
            filename = output_dir / f"card_{card_name.lower().replace(' ', '_')}_{set_code}_draft_picks.csv"
            draft_picks_df.to_csv(filename, index=False)
            print(f"  Exported {len(draft_picks_df)} draft picks to: {filename}")
        
        # Export game data sample
        game_data_df = pd.read_sql_query("""
            SELECT 
                gr.game_id, gr.draft_id, gr.won, gr.num_turns,
                gr.main_colors, gr.opp_colors, gr.rank,
                gc.in_opening_hand, gc.was_drawn, gc.in_maindeck
            FROM game_cards gc
            JOIN game_results gr ON gc.game_id = gr.game_id
            WHERE gc.card_id = ? AND gr."set" = ?
            ORDER BY gr.game_time DESC
            LIMIT 1000
        """, conn, params=(card_id, set_code))
        if not game_data_df.empty:
            filename = output_dir / f"card_{card_name.lower().replace(' ', '_')}_{set_code}_game_data.csv"
            game_data_df.to_csv(filename, index=False)
            print(f"  Exported {len(game_data_df)} game records to: {filename}")
        
        # Export archetype performance
        archetype_df = pd.read_sql_query("""
            SELECT DISTINCT
                ca.main_colors,
                ca.splash_colors,
                ca.win_rate as archetype_wr,
                ca.total_games as archetype_games,
                COUNT(DISTINCT ds.draft_id) as drafts_with_card,
                AVG(ds.win_rate) as avg_draft_wr_with_card
            FROM color_archetypes ca
            JOIN draft_summaries ds ON ca.main_colors = ds.final_colors 
                AND (ca.splash_colors = ds.splash_colors OR (ca.splash_colors IS NULL AND ds.splash_colors IS NULL))
            JOIN draft_picks dp ON ds.draft_id = dp.draft_id
            WHERE dp.card_id = ? 
                AND ca."set" = ?
                AND ds."set" = ?
            GROUP BY ca.main_colors, ca.splash_colors, ca.win_rate, ca.total_games
            ORDER BY ca.win_rate DESC
        """, conn, params=(card_id, set_code, set_code))
        if not archetype_df.empty:
            filename = output_dir / f"card_{card_name.lower().replace(' ', '_')}_{set_code}_archetypes.csv"
            archetype_df.to_csv(filename, index=False)
            print(f"  Exported {len(archetype_df)} archetype records to: {filename}")
        
        print("\n" + "=" * 80)
        print("QUERY COMPLETE")
        print("=" * 80)
        return True

def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python query_card_comprehensive.py <CARD_NAME> <SET_CODE> [DB_PATH]")
        print("Example: python query_card_comprehensive.py 'Invasion Submersible' TLA")
        print("Example: python query_card_comprehensive.py 'Lightning Bolt' MOM mtg_draft_coach.db")
        sys.exit(1)
    
    card_name = sys.argv[1]
    set_code = sys.argv[2].upper()
    db_path = sys.argv[3] if len(sys.argv) > 3 else "mtg_draft_coach.db"
    
    success = query_card_comprehensive(card_name, set_code, db_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

