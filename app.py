import streamlit as st
import pandas as pd

st.set_page_config(page_title="Yom Habocher - Playoff Bracket 2026", layout="wide")

# ==========================================
# 1. PLAY-IN POINTS
# ==========================================
PLAYIN_POINTS = {
    "Youval": 25, "Ofer": 25, "Siton": 20, "Ori": 15, "Nadav": 15,
    "Elad Klein": 35, "Shalev": 35, "Pongo": 25, "Noga Siton": 25,
    "Rafael": 25, "Or David": 25, "Raz": 30           
}

# ==========================================
# 2. ACTUAL RESULTS
# ==========================================
ACTUAL_RESULTS = {
    # WEST ROUND 1
    "West_R1_1": {"team1": "OKC", "team2": "PHX", "team1_wins": 4, "team2_wins": 0},
    "West_R1_2": {"team1": "HOU", "team2": "LAL", "team1_wins": 2, "team2_wins": 4},
    "West_R1_3": {"team1": "DEN", "team2": "MIN", "team1_wins": 2, "team2_wins": 4},
    "West_R1_4": {"team1": "SAS", "team2": "POR", "team1_wins": 4, "team2_wins": 1},
    
    # EAST ROUND 1
    "East_R1_1": {"team1": "DET", "team2": "ORL", "team1_wins": 4, "team2_wins": 3},
    "East_R1_2": {"team1": "CLE", "team2": "TOR", "team1_wins": 4, "team2_wins": 3},
    "East_R1_3": {"team1": "NYK", "team2": "ATL", "team1_wins": 4, "team2_wins": 2},
    "East_R1_4": {"team1": "BOS", "team2": "PHI", "team1_wins": 2, "team2_wins": 4},
    
    # FUTURE ROUNDS
    "West_R2_1": {"team1": "OKC", "team2": "LAL", "team1_wins": 4, "team2_wins": 0}, 
    "West_R2_2": {"team1": "SAS", "team2": "MIN", "team1_wins": 0, "team2_wins": 0}, 
    "West_CF":   None, 
    "East_R2_1": {"team1": "DET", "team2": "CLE", "team1_wins": 0, "team2_wins": 0}, 
    "East_R2_2": {"team1": "PHI", "team2": "NYK", "team1_wins": 0, "team2_wins": 4}, 
    "East_CF":   None, 
    "CHAMPION":  None  
}

BRACKET_STRUCTURE = {
    "West_R2_1": ("West_R1_1", "West_R1_2"), "West_R2_2": ("West_R1_3", "West_R1_4"),
    "East_R2_1": ("East_R1_1", "East_R1_2"), "East_R2_2": ("East_R1_3", "East_R1_4"),
    "West_CF": ("West_R2_1", "West_R2_2"), "East_CF": ("East_R2_1", "East_R2_2"),
    "CHAMPION": ("West_CF", "East_CF")
}

def get_eliminated_teams(actual_results):
    eliminated = set()
    for state in actual_results.values():
        if state is not None:
            if state["team1_wins"] == 4: eliminated.add(state["team2"])
            elif state["team2_wins"] == 4: eliminated.add(state["team1"])
    return eliminated

# ==========================================
# 3. SCORING SYSTEM & LOGIC (UPDATED RULE)
# ==========================================
POINTS_PER_ROUND = {'R1': 10, 'R2': 20, 'CF': 30, 'CHAMPION': 50}

def calculate_finished_score(predicted, actual_winner, actual_games, round_type, is_matchup_correct):
    score = 0
    # 1. Did they get the winner right?
    if predicted["winner"] == actual_winner:
        score += POINTS_PER_ROUND[round_type]
        
        # 2. Bonus points ONLY if the matchup was 100% correct
        if is_matchup_correct:
            games_diff = abs(predicted["games"] - actual_games)
            if games_diff == 0: score += 10
            elif games_diff == 1: score += 5
            
    return score

def get_possible_scores(predicted, t1, w1, t2, w2, round_type, is_matchup_correct):
    if w1 == 4: return [calculate_finished_score(predicted, t1, w1 + w2, round_type, is_matchup_correct)]
    if w2 == 4: return [calculate_finished_score(predicted, t2, w1 + w2, round_type, is_matchup_correct)]
    
    scores = []
    scores.extend(get_possible_scores(predicted, t1, w1 + 1, t2, w2, round_type, is_matchup_correct))
    scores.extend(get_possible_scores(predicted, t1, w1, t2, w2 + 1, round_type, is_matchup_correct))
    return scores

def score_matchup(match_key, pick_data, all_player_picks, state, round_type, eliminated_teams):
    # Dead team check
    if pick_data["winner"] in eliminated_teams:
        return 0, 0

    # Figure out what matchup the player PREDICTED would happen
    if "R1" in match_key:
        predicted_teams = {state["team1"], state["team2"]} if state else set()
    else:
        src1, src2 = BRACKET_STRUCTURE[match_key]
        predicted_teams = {all_player_picks[src1]["winner"], all_player_picks[src2]["winner"]}

    if state is None:
        # Round hasn't started. Max potential assumes their dream scenario happens exactly.
        return 0, POINTS_PER_ROUND[round_type] + 10
        
    t1, t2 = state["team1"], state["team2"]
    w1, w2 = state["team1_wins"], state["team2_wins"]
    actual_teams = {t1, t2}
    
    # NEW RULE: Is the matchup exactly what they thought it would be?
    is_matchup_correct = (predicted_teams == actual_teams)
    
    if w1 == 4 or w2 == 4:
        winner = t1 if w1 == 4 else t2
        final_score = calculate_finished_score(pick_data, winner, w1 + w2, round_type, is_matchup_correct)
        return final_score, final_score
        
    if pick_data["winner"] not in actual_teams:
        return 0, 0 
        
    possible_scores = get_possible_scores(pick_data, t1, w1, t2, w2, round_type, is_matchup_correct)
    return 0, max(possible_scores)

def score_full_bracket(player_name, player_bracket, actual_results, eliminated_teams):
    current_total = PLAYIN_POINTS.get(player_name, 0)
    potential_total = PLAYIN_POINTS.get(player_name, 0)
    
    for matchup_key, predicted_data in player_bracket.items():
        if "R1" in matchup_key: round_type = "R1"
        elif "R2" in matchup_key: round_type = "R2"
        elif "CF" in matchup_key: round_type = "CF"
        else: round_type = "CHAMPION"
            
        state = actual_results.get(matchup_key)
        realized, potential = score_matchup(matchup_key, predicted_data, player_bracket, state, round_type, eliminated_teams)
        
        current_total += realized
        potential_total += potential
        
    return current_total, potential_total

# ==========================================
# 4. PLAYER DATA 
# ==========================================
def build_picks(w_r1, w_r2, w_cf, e_r1, e_r2, e_cf, champ):
    return {
        "West_R1_1": {"winner": w_r1[0][0], "games": w_r1[0][1]}, "West_R1_2": {"winner": w_r1[1][0], "games": w_r1[1][1]},
        "West_R1_3": {"winner": w_r1[2][0], "games": w_r1[2][1]}, "West_R1_4": {"winner": w_r1[3][0], "games": w_r1[3][1]},
        "West_R2_1": {"winner": w_r2[0][0], "games": w_r2[0][1]}, "West_R2_2": {"winner": w_r2[1][0], "games": w_r2[1][1]},
        "West_CF":   {"winner": w_cf[0], "games": w_cf[1]},
        "East_R1_1": {"winner": e_r1[0][0], "games": e_r1[0][1]}, "East_R1_2": {"winner": e_r1[1][0], "games": e_r1[1][1]},
        "East_R1_3": {"winner": e_r1[2][0], "games": e_r1[2][1]}, "East_R1_4": {"winner": e_r1[3][0], "games": e_r1[3][1]},
        "East_R2_1": {"winner": e_r2[0][0], "games": e_r2[0][1]}, "East_R2_2": {"winner": e_r2[1][0], "games": e_r2[1][1]},
        "East_CF":   {"winner": e_cf[0], "games": e_cf[1]}, "CHAMPION":  {"winner": champ[0], "games": champ[1]}
    }

players = [
    {"name": "Youval", "picks": build_picks([("OKC", 5), ("HOU", 5), ("DEN", 7), ("SAS", 4)], [("OKC", 5), ("DEN", 7)], ("OKC", 5), [("DET", 5), ("TOR", 6), ("NYK", 7), ("BOS", 5)], [("DET", 5), ("BOS", 5)], ("DET", 7), ("OKC", 7))},
    {"name": "Ofer", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 5), ("POR", 7)], [("OKC", 4), ("DEN", 5)], ("OKC", 6), [("DET", 5), ("CLE", 5), ("NYK", 6), ("BOS", 4)], [("DET", 7), ("BOS", 5)], ("BOS", 6), ("OKC", 6))},
    {"name": "Siton", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 6), ("SAS", 4)], [("OKC", 4), ("DEN", 7)], ("OKC", 7), [("DET", 7), ("CLE", 6), ("NYK", 5), ("BOS", 4)], [("CLE", 6), ("BOS", 6)], ("BOS", 5), ("OKC", 7))},
    {"name": "Raz", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 6), ("SAS", 4)], [("OKC", 4), ("DEN", 7)], ("OKC", 7), [("DET", 7), ("CLE", 6), ("NYK", 5), ("BOS", 4)], [("CLE", 6), ("BOS", 6)], ("BOS", 5), ("OKC", 6))}, 
    {"name": "Ori", "picks": build_picks([("OKC", 6), ("HOU", 5), ("DEN", 7), ("SAS", 5)], [("OKC", 7), ("SAS", 6)], ("SAS", 7), [("DET", 5), ("CLE", 7), ("NYK", 5), ("BOS", 5)], [("CLE", 6), ("NYK", 6)], ("NYK", 7), ("SAS", 5))},
    {"name": "Nadav", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 7), ("SAS", 7)], [("OKC", 5), ("DEN", 6)], ("DEN", 6), [("DET", 4), ("CLE", 4), ("NYK", 5), ("BOS", 5)], [("CLE", 7), ("BOS", 5)], ("BOS", 7), ("DEN", 6))},
    {"name": "Elad Klein", "picks": build_picks([("OKC", 5), ("HOU", 6), ("DEN", 7), ("SAS", 5)], [("OKC", 6), ("SAS", 6)], ("SAS", 6), [("DET", 5), ("CLE", 5), ("NYK", 6), ("BOS", 6)], [("DET", 5), ("NYK", 6)], ("DET", 6), ("SAS", 6))},
    {"name": "Shalev", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 7), ("SAS", 5)], [("OKC", 6), ("DEN", 6)], ("OKC", 7), [("DET", 5), ("CLE", 7), ("NYK", 6), ("BOS", 5)], [("DET", 7), ("BOS", 6)], ("BOS", 6), ("OKC", 6))},
    {"name": "Pongo", "picks": build_picks([("OKC", 4), ("HOU", 4), ("DEN", 7), ("SAS", 5)], [("OKC", 5), ("SAS", 7)], ("OKC", 6), [("DET", 5), ("CLE", 5), ("NYK", 6), ("BOS", 5)], [("DET", 7), ("BOS", 7)], ("DET", 7), ("OKC", 5))},
    {"name": "Or David", "picks": build_picks([("OKC", 5), ("HOU", 5), ("DEN", 6), ("SAS", 4)], [("OKC", 6), ("DEN", 7)], ("OKC", 6), [("DET", 5), ("CLE", 5), ("NYK", 5), ("BOS", 5)], [("CLE", 6), ("BOS", 5)], ("BOS", 5), ("OKC", 6))},
    {"name": "Noga Siton", "picks": build_picks([("OKC", 7), ("HOU", 6), ("DEN", 6), ("SAS", 6)], [("OKC", 7), ("DEN", 7)], ("OKC", 7), [("ORL", 7), ("TOR", 7), ("NYK", 4), ("BOS", 5)], [("ORL", 4), ("NYK", 7)], ("ORL", 7), ("OKC", 4))},
    {"name": "Rafael", "picks": build_picks([("OKC", 4), ("HOU", 6), ("DEN", 7), ("SAS", 5)], [("OKC", 5), ("SAS", 6)], ("SAS", 7), [("DET", 4), ("CLE", 6), ("NYK", 6), ("BOS", 6)], [("DET", 7), ("BOS", 6)], ("BOS", 7), ("SAS", 6))}
]

# ==========================================
# 5. UI HELPER: MATCHUP CARD RENDERING
# ==========================================
def render_matchup_card(match_key, pick_data, all_player_picks, state, round_type, eliminated_teams):
    realized, potential = score_matchup(match_key, pick_data, all_player_picks, state, round_type, eliminated_teams)
    
    bg_color, border_color, text_color = "#1E1E1E", "#333", "#FFF"
    actual_str, pts_str = "TBD vs TBD", f"⏳ Pot: {potential}"

    if state is not None:
        t1, t2 = state["team1"], state["team2"]
        w1, w2 = state["team1_wins"], state["team2_wins"]
        actual_str = f"{t1} ({w1}) - {t2} ({w2})"
        
        if w1 == 4 or w2 == 4:
            if realized > 0:
                bg_color, border_color, text_color, pts_str = "#143a1d", "#28a745", "#d4edda", f"✅ +{realized} pts"
            else:
                bg_color, border_color, text_color, pts_str = "#3a1416", "#dc3545", "#f8d7da", "❌ 0 pts"
        else:
            bg_color, border_color, text_color, pts_str = "#142c47", "#0056b3", "#cce5ff", f"🔄 Max: {potential}"
    else:
        if potential == 0:
            bg_color, border_color, text_color, pts_str = "#3a1416", "#dc3545", "#f8d7da", "❌ 0 pts"

    card_html = f"""
    <div style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color}; padding: 10px; border-radius: 8px; margin-bottom: 12px;">
        <div style="font-size: 0.85em; text-transform: uppercase; font-weight: bold; margin-bottom: 8px; opacity: 0.8;">{match_key.replace('_', ' ')}</div>
        <div style="display: flex; justify-content: space-between; font-size: 0.95em; margin-bottom: 4px;">
            <span><b>Pick:</b> {pick_data['winner']} in {pick_data['games']}</span>
            <span style="font-weight: bold;">{pts_str}</span>
        </div>
        <div style="font-size: 0.9em; opacity: 0.9;"><b>Actual:</b> {actual_str}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ==========================================
# 6. STREAMLIT APP UI
# ==========================================
st.title("🏆 Yom Habocher - Playoff Bracket 2026")
st.markdown("**Includes Play-in points + Live 'Potential Points' tracker!**")

eliminated_teams = get_eliminated_teams(ACTUAL_RESULTS)

leaderboard_data = []
for p in players:
    current_pts, potential_pts = score_full_bracket(p["name"], p["picks"], ACTUAL_RESULTS, eliminated_teams)
    
    leaderboard_data.append({
        "Player": p["name"], 
        "Current Points": current_pts, 
        "Max Potential": potential_pts,
        "Play-in Pts": PLAYIN_POINTS.get(p["name"], 0),
        "Champion Pick": p["picks"]["CHAMPION"]["winner"]
    })

df_leaderboard = pd.DataFrame(leaderboard_data).sort_values(by=["Current Points", "Max Potential"], ascending=False).reset_index(drop=True)
df_leaderboard.index += 1

st.subheader("Live Leaderboard 📊")
st.dataframe(df_leaderboard, use_container_width=True)

st.divider()
st.subheader("Everyone's Brackets 🏀")

for p in players:
    with st.expander(f"👀 View {p['name']}'s Bracket"):
        st.markdown(f"**🎯 Play-in Points:** {PLAYIN_POINTS.get(p['name'], 0)} pts")
        col_east, col_west = st.columns(2)
        
        with col_east:
            st.markdown("<h3 style='text-align: center; color: #4b89ff;'>🔵 EASTERN CONFERENCE</h3>", unsafe_allow_html=True)
            st.markdown("#### Round 1")
            for key in ["East_R1_1", "East_R1_2", "East_R1_3", "East_R1_4"]:
                render_matchup_card(key, p["picks"][key], p["picks"], ACTUAL_RESULTS[key], "R1", eliminated_teams)
                
            st.markdown("#### Conference Semifinals")
            for key in ["East_R2_1", "East_R2_2"]:
                render_matchup_card(key, p["picks"][key], p["picks"], ACTUAL_RESULTS[key], "R2", eliminated_teams)
                
            st.markdown("#### Conference Finals")
            render_matchup_card("East_CF", p["picks"]["East_CF"], p["picks"], ACTUAL_RESULTS["East_CF"], "CF", eliminated_teams)

        with col_west:
            st.markdown("<h3 style='text-align: center; color: #ff4b4b;'>🔴 WESTERN CONFERENCE</h3>", unsafe_allow_html=True)
            st.markdown("#### Round 1")
            for key in ["West_R1_1", "West_R1_2", "West_R1_3", "West_R1_4"]:
                render_matchup_card(key, p["picks"][key], p["picks"], ACTUAL_RESULTS[key], "R1", eliminated_teams)
                
            st.markdown("#### Conference Semifinals")
            for key in ["West_R2_1", "West_R2_2"]:
                render_matchup_card(key, p["picks"][key], p["picks"], ACTUAL_RESULTS[key], "R2", eliminated_teams)
                
            st.markdown("#### Conference Finals")
            render_matchup_card("West_CF", p["picks"]["West_CF"], p["picks"], ACTUAL_RESULTS["West_CF"], "CF", eliminated_teams)
            
        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>🏆 NBA FINALS 🏆</h3>", unsafe_allow_html=True)
        col_spacer1, col_champ, col_spacer2 = st.columns([1, 2, 1])
        with col_champ:
            render_matchup_card("CHAMPION", p["picks"]["CHAMPION"], p["picks"], ACTUAL_RESULTS["CHAMPION"], "CHAMPION", eliminated_teams)