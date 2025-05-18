import pickle
import random
import numpy as np
import os
from flask import Flask, render_template, jsonify, session, url_for

# --- PokerEvaluator Class (Copied from your original code, largely unchanged) ---
class PokerEvaluator:
    # Hand rankings
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_KIND = 7
    STRAIGHT_FLUSH = 8

    def __init__(self):
        self.RANK_VALUES = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
            "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
        }

    def evaluate_hand(self, hole_cards, community_cards):
        all_cards = hole_cards + community_cards
        if not all_cards or len(all_cards) < 5:
            return None # Not enough cards to evaluate

        combinations = []
        # Ensure cards are strings for consistency if they come from different sources
        processed_cards = []
        for card in all_cards:
            if isinstance(card, tuple): # e.g. ('A', 'h')
                processed_cards.append(f"{card[0]}{card[1]}")
            elif isinstance(card, dict): # e.g. {'rank': 'A', 'suit': 'h'}
                 processed_cards.append(f"{card['rank']}{card['suit']}")
            else: # e.g. "Ah"
                processed_cards.append(card)

        self.generate_combinations(processed_cards, 5, 0, [], combinations)

        best_score = None
        for combo in combinations:
            score = self.evaluate_five_card_hand(combo)
            if best_score is None or (score and score > best_score):
                best_score = score
        return best_score

    def evaluate_five_card_hand(self, hand):
        if not hand or len(hand) != 5: return None

        # Convert string cards to values
        # Ensure hand items are strings like "Kh" or "10s"
        card_values = []
        for card_str in hand:
            rank_str = card_str[:-1] # "K", "10"
            if rank_str not in self.RANK_VALUES:
                # print(f"Warning: Unknown rank {rank_str} in card {card_str}")
                return None # Invalid card
            card_values.append(self.RANK_VALUES[rank_str])

        card_values.sort(reverse=True)

        freq = {}
        for v in card_values:
            freq[v] = freq.get(v, 0) + 1
        freq_sorted = sorted(freq.items(), key=lambda x: (x[1], x[0]), reverse=True)

        is_flush = self.check_flush(hand)
        straight_high = [0]
        is_straight = self.check_straight(card_values, straight_high)

        if is_flush and is_straight:
            return [self.STRAIGHT_FLUSH, straight_high[0]]
        if freq_sorted[0][1] == 4:
            kicker = next((v for v in card_values if v != freq_sorted[0][0]), 0) # Default kicker
            return [self.FOUR_KIND, freq_sorted[0][0], kicker]
        if freq_sorted[0][1] == 3 and len(freq_sorted) > 1 and freq_sorted[1][1] >= 2:
            return [self.FULL_HOUSE, freq_sorted[0][0], freq_sorted[1][0]]
        if is_flush:
            return [self.FLUSH] + card_values[:5] # Ensure only 5 cards
        if is_straight:
            return [self.STRAIGHT, straight_high[0]]
        if freq_sorted[0][1] == 3:
            kickers = [v for v in card_values if v != freq_sorted[0][0]]
            return [self.THREE_KIND, freq_sorted[0][0]] + kickers[:2] # Ensure 2 kickers
        if freq_sorted[0][1] == 2 and len(freq_sorted) > 1 and freq_sorted[1][1] == 2:
            kicker = next((v for v in card_values if v != freq_sorted[0][0] and v != freq_sorted[1][0]), 0)
            # Ensure pairs are sorted if ranks are different
            pair1_val = freq_sorted[0][0]
            pair2_val = freq_sorted[1][0]
            return [self.TWO_PAIR, max(pair1_val, pair2_val), min(pair1_val, pair2_val), kicker]
        if freq_sorted[0][1] == 2:
            kickers = [v for v in card_values if v != freq_sorted[0][0]]
            return [self.PAIR, freq_sorted[0][0]] + kickers[:3] # Ensure 3 kickers
        return [self.HIGH_CARD] + card_values[:5] # Ensure 5 cards

    def generate_combinations(self, cards, combination_size, start, current_combo, all_combinations):
        if len(current_combo) == combination_size:
            all_combinations.append(current_combo[:])
            return
        if start >= len(cards):
            return
        for i in range(start, len(cards) - (combination_size - len(current_combo)) + 1):
            current_combo.append(cards[i])
            self.generate_combinations(cards, combination_size, i + 1, current_combo, all_combinations)
            current_combo.pop()

    def check_flush(self, hand):
        if not hand: return False
        suit = hand[0][-1]
        return all(c[-1] == suit for c in hand)

    def check_straight(self, values, high_straight_value):
        # values should be numeric and sorted for this function
        unique_sorted_values = sorted(list(set(values)), reverse=True) # Ace can be high or low

        # Check for standard straight (5 unique ranks in sequence)
        for i in range(len(unique_sorted_values) - 4):
            is_seq = True
            for j in range(4):
                if unique_sorted_values[i+j] - unique_sorted_values[i+j+1] != 1:
                    is_seq = False
                    break
            if is_seq:
                high_straight_value[0] = unique_sorted_values[i]
                return True

        # Check for A-5 straight (wheel: A, 5, 4, 3, 2)
        # Numeric values: 14, 5, 4, 3, 2
        if set([14, 5, 4, 3, 2]).issubset(set(values)):
             # Check if these 5 distinct cards form the wheel
            wheel_ranks = [14, 5, 4, 3, 2]
            hand_ranks_for_wheel_check = sorted(list(set(v for v in values if v in wheel_ranks)), reverse=True)
            if len(hand_ranks_for_wheel_check) >= 5: # Ensure we have at least 5 cards for a straight
                # Check if the highest 5 cards that could form a wheel actually do
                # This logic is tricky with 7 cards. We need to find if ANY 5 cards form a straight.
                # The main evaluate_hand generates 5-card combos, so check_straight receives 5 values.
                # For a 5-card hand:
                if sorted(values) == [2,3,4,5,14]: # Ace is high (14)
                    high_straight_value[0] = 5 # Ace is low in A-5 straight
                    return True
        return False

    def hand_type_to_string(self, hand_type_val):
        types = {
            self.HIGH_CARD: "High Card", self.PAIR: "Pair", self.TWO_PAIR: "Two Pair",
            self.THREE_KIND: "Three of a Kind", self.STRAIGHT: "Straight", self.FLUSH: "Flush",
            self.FULL_HOUSE: "Full House", self.FOUR_KIND: "Four of a Kind",
            self.STRAIGHT_FLUSH: "Straight Flush"
        }
        return types.get(hand_type_val, "Unknown Hand")
# --- End PokerEvaluator Class ---


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

app.secret_key = os.urandom(24)

evaluator = PokerEvaluator()
RANKS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
SUITS = ['h', 'd', 'c', 's'] # hearts, diamonds, clubs, spades

# Load hand data (strategy)
def load_results():
    try:
        with open('aggregated_results.pkl', 'rb') as f:
            data = pickle.load(f)
            # print(f"[DEBUG_LOAD_RESULTS] Successfully loaded aggregated_results.pkl.")
            # print(f"[DEBUG_LOAD_RESULTS] Number of entries in HAND_DATA_STRATEGY: {len(data)}")
            # Print a sample entry if data is not empty
            # if data:
            #     sample_key = next(iter(data))
            #     sample_value = data[sample_key]
            #     #print(f"[DEBUG_LOAD_RESULTS] Sample entry - Key: {sample_key}, Value: {sample_value}")
            # else:
            #     #print("[DEBUG_LOAD_RESULTS] HAND_DATA_STRATEGY is empty after loading.")
            return data
    except FileNotFoundError:
        print("Warning: aggregated_results.pkl not found. Using empty dictionary.")
        return {}
    except Exception as e:
        print(f"Error loading or reading aggregated_results.pkl: {e}")
        #print("[DEBUG_LOAD_RESULTS] Using empty dictionary due to error.")
        return {}
HAND_DATA_STRATEGY = load_results()

# Helper function to convert app's hand string format to the strategy lookup format
def convert_hand_to_lookup_format(hand_str_app):
    """
    Converts hand string from app's format (e.g., "A10s", "KQs")
    to strategy lookup format (e.g., "A Ts", "K Qs").
    Assumes strategy keys use 'T' for Ten and a space separator.
    """
    ranks = {"2" : 2, "3" : 3, "4" : 4, "5" : 5, "6" : 6, "7" : 7, "8" : 8, "9" : 9, "10" : 10, "J" : 11, "Q" : 12, "K" : 13, "A" : 14}
    # After replacement, the rank part (e.g., "AT", "KQ", "T9") is expected to be two characters.
    # hand_str_app could be "AKs" (3 chars) or "A10s" (4 chars).
    # processed_hand_str will be 3 chars, e.g., "AKs" or "ATs".
    if ranks.get(hand_str_app[0], 0) < ranks.get(hand_str_app[1], 0):
        rank1_char = hand_str_app[0]
        rank2_char = hand_str_app[1]
    else:
        rank1_char = hand_str_app[1]
        rank2_char = hand_str_app[0]
    suit_info = hand_str_app[2]
    
    return f"{rank1_char} {rank2_char}{suit_info}"

# Helper function to generate the infoset string for strategy lookup
def generate_infoset_for_lookup(prior_actions):
    """
    Generates the infoset string based on prior player actions.
    prior_actions: list of decisions ("ALL_IN" or "FOLD") from CO, BTN, SB in order.
    Player IDs in infoset (P0, P1, P2, P3) map to (CO, BTN, SB, BB).
    """
    num_prior = len(prior_actions)
    
    if num_prior == 0:  # Current player is CO
        # This is the typical starting infoset for the first actor (CO)
        return "P2:[P0:P][P1:P]"
        
    elif num_prior == 1:  # Current player is BTN (CO has acted)
        co_act_char = 'A' if prior_actions[0] == 'ALL_IN' else 'F'
        # Infoset for BTN, given CO's action (P2 refers to CO in this context)
        return f"P3:[P0:P][P1:P][P2:{co_act_char}]"
        
    elif num_prior == 2:  # Current player is SB (CO and BTN have acted)
        co_act_char = 'A' if prior_actions[0] == 'ALL_IN' else 'F'
        btn_act_char = 'A' if prior_actions[1] == 'ALL_IN' else 'F'
        # Infoset for SB, given CO (P2) and BTN (P3) actions
        return f"P0:[P1:P][P2:{co_act_char}][P3:{btn_act_char}]"
        
    elif num_prior == 3:  # Current player is BB (CO, BTN, SB have acted)
        co_act_char = 'A' if prior_actions[0] == 'ALL_IN' else 'F'
        btn_act_char = 'A' if prior_actions[1] == 'ALL_IN' else 'F'
        sb_act_char = 'A' if prior_actions[2] == 'ALL_IN' else 'F'
        # Infoset for BB, given CO (P0), BTN (P2), and SB (P3) actions
        return f"P1:[P0:{co_act_char}][P2:{btn_act_char}][P3:{sb_act_char}]"
    
    # Fallback, though for a 4-player game, num_prior should be 0, 1, 2, or 3.
    print(f"Warning: Unexpected number of prior actions ({num_prior}) for infoset generation.")
    return "ERROR_UNKNOWN_INFOSET_CONDITION"

# Helper function to find card image files with various naming conventions
def find_card_image_filename(card_str):
    """
    Tries to find an existing card image file based on the card string.
    card_str: e.g., "9h", "AS", "10d"
    Returns the filename (e.g., "9H.png") if found, or a default if not.
    """
    if not card_str or len(card_str) < 2:
        #print(f"[CARD_IMG_DEBUG] Invalid card_str: {card_str}, returning back.png")
        return "back.png"  # Should ideally not happen with valid card strings

    rank_part = card_str[:-1]  # e.g., "9", "A", "10"
    suit_part = card_str[-1]   # e.g., "h", "S", "d" (suit from input string)
    #print(f"[CARD_IMG_DEBUG] Finding image for card_str: '{card_str}' (Rank: '{rank_part}', Suit: '{suit_part}')")

    base_image_path = os.path.join('static', 'card_images')

    # Patterns to try:
    patterns_to_try = [
        f"{rank_part}{suit_part.lower()}.png",          # Rs (e.g. Ah.png, 10s.png)
        f"{rank_part.lower()}{suit_part.lower()}.png",  # rs (e.g. ah.png, 10s.png)
        f"{rank_part}{suit_part.upper()}.png",          # RSU (e.g. AH.png, 10S.png)
        f"{rank_part.lower()}{suit_part.upper()}.png",  # rsU (e.g. aH.png, 10S.png)
    ]

    unique_patterns = []
    for p in patterns_to_try:
        if p not in unique_patterns:
            unique_patterns.append(p)
    
    #print(f"[CARD_IMG_DEBUG] Trying patterns for '{card_str}': {unique_patterns}")

    for pattern_filename in unique_patterns:
        full_path = os.path.join(base_image_path, pattern_filename)
        # print(f"[CARD_IMG_DEBUG] Checking for: '{full_path}'") # Optional: very verbose
        if os.path.exists(full_path):
            #print(f"[CARD_IMG_DEBUG] Found existing image for '{card_str}': '{pattern_filename}' at path '{full_path}'")
            return pattern_filename
        # else: # Optional: very verbose
            # print(f"[CARD_IMG_DEBUG] Image not found: '{pattern_filename}' at path '{full_path}'")

    # Fallback if no image found after trying all patterns
    default_filename = f"{rank_part}{suit_part.lower()}.png" # Default to Rank + lowercase suit
    print(f"[CARD_IMG_DEBUG] No image found for '{card_str}' using patterns. Defaulting to '{default_filename}' and expecting it at '{os.path.join(base_image_path, default_filename)}'")
    return default_filename

def get_initial_game_state():
    return {
        "players": ["CO", "BTN", "SB", "BB"],
        "player_stacks": [8.0, 8.0, 8.0, 8.0], # Starting stacks in BB
        "current_player_idx": 0, # User is always current_player_idx for decision
        "user_player_position_idx": 0, # Actual position of the user (CO, BTN, SB, BB)
        "user_player_position_idx_last_hand": 0, # Added: User's position in the hand just played/being played
        "hands_played": 0,
        "all_player_cards": [], # List of 2-card lists, e.g., [["AH", "KD"], ["QC", "JS"], ...]
        "community_cards": [], # List of 5 cards, e.g., ["2S", "3H", "4D", "5C", "6S"]
        "decisions": [""] * 4, # Initialize with empty strings for 4 players
        "pot_size": 0.0,
        "small_blind": 0.4,
        "big_blind": 1.0,
        "log_messages": ["Game started! Click 'Deal New Hand' to begin."],
        "game_phase": "pre_deal", # "pre_deal", "awaiting_decision", "showdown"
        "player_cumulative_bb": [0], # For the graph - starts at 0
        "winner_info": None, # To store winner details for display
        "winners_player_indices": [], # Added: To store indices of winning players
        "revealed_cards": {}, # player_idx: [card1, card2] for showdown
        "player_bets_this_hand": [0.0, 0.0, 0.0, 0.0] # Tracks total bets for each player in the current hand
    }

def get_game_state():
    if 'game_state' not in session:
        session['game_state'] = get_initial_game_state()
    # Ensure all keys are present, useful for upgrades
    default_state = get_initial_game_state()
    for key, value in default_state.items():
        session['game_state'].setdefault(key, value)
    return session['game_state']

def save_game_state(state):
    session['game_state'] = state
    session.modified = True


def log_message(state, message):
    state["log_messages"].append(message)
    if len(state["log_messages"]) > 10: # Keep log concise
        state["log_messages"].pop(0)

def format_hand_for_strategy(cards_list):
    # cards_list is like ["AH", "KS"]
    if not cards_list or len(cards_list) != 2:
        return "Unknown"
    card1_rank = cards_list[0][:-1]
    card1_suit = cards_list[0][-1]
    card2_rank = cards_list[1][:-1]
    card2_suit = cards_list[1][-1]

    suited = 's' if card1_suit == card2_suit else 'o'
    
    rank_values = evaluator.RANK_VALUES
    # Order by rank (higher rank first)
    if rank_values.get(card1_rank, 0) > rank_values.get(card2_rank, 0):
        return f"{card2_rank} {card1_rank}{suited}"
    return f"{card1_rank} {card2_rank}{suited}"


def simulate_optimal_decision(player_position_name, player_hand_str, state):
    # player_position_name is "CO", "BTN", "SB", "BB"
    # player_hand_str is "AKs", "107o", etc. (from format_hand_for_strategy)
    # state is the current game state
    #print(f"\n[DEBUG_SIMULATE_DECISION] Simulating for: {player_position_name}, Hand: {player_hand_str}")

    player_map = {"CO": 0, "BTN": 1, "SB": 2, "BB": 3}
    current_player_game_idx = player_map.get(player_position_name)

    if current_player_game_idx is None:
        print(f"Warning: Unknown player position '{player_position_name}' in simulate_optimal_decision. Defaulting to FOLD.")
        return "FOLD"

    # Get decisions of players who acted before the current player
    # state["decisions"] stores actions for CO, BTN, SB, BB by their game index
    prior_raw_decisions = state["decisions"][:current_player_game_idx]
    
    # Ensure prior decisions are valid ("ALL_IN" or "FOLD"), default to "FOLD" if empty/unexpected
    prior_actions_for_infoset = []
    for dec in prior_raw_decisions:
        if dec in ["ALL_IN", "FOLD"]:
            prior_actions_for_infoset.append(dec)
        else:
            # If a prior player's decision isn't set or is invalid, assume FOLD for infoset robustness
            # This might happen if state["decisions"] wasn't fully populated as expected
            prior_actions_for_infoset.append("FOLD") 


    infoset_key = generate_infoset_for_lookup(prior_actions_for_infoset)
    hand_key = player_hand_str # Convert "A10s" to "A Ts"
    #print(f"[DEBUG_SIMULATE_DECISION] Infoset Key for lookup: '{infoset_key}'")
    #print(f"[DEBUG_SIMULATE_DECISION] Hand Key for lookup: '{hand_key}'")

    # The strategy data is expected to store (fold_probability, all_in_probability)
    # Default to 50/50 fold/all-in if the specific situation is not in the strategy
    default_probabilities = (0.5, 0.5) # Default if key not found
    retrieved_probabilities = HAND_DATA_STRATEGY.get((infoset_key, hand_key), default_probabilities)
    
    fold_prob, all_in_prob = retrieved_probabilities
    
    # if retrieved_probabilities == default_probabilities and (infoset_key, hand_key) not in HAND_DATA_STRATEGY:
    #     print(f"[DEBUG_SIMULATE_DECISION] Key ({infoset_key}, {hand_key}) not found in HAND_DATA_STRATEGY. Using default probabilities: {default_probabilities}")
    # else:
    #     print(f"[DEBUG_SIMULATE_DECISION] Retrieved probabilities for ({infoset_key}, {hand_key}): Fold Prob={fold_prob}, All-In Prob={all_in_prob}")
    
    # Decision logic based on all_in_prob, as seen in the provided simulation code
    decision = "FOLD" # Default decision
    if random.random() < all_in_prob:
        decision = "ALL_IN"
    
    #print(f"[DEBUG_SIMULATE_DECISION] Simulated decision: {decision} (random draw vs all_in_prob {all_in_prob})")
    return decision

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_state', methods=['GET'])
def get_state_api():
    state = get_game_state()
    display_state = state.copy()
    
    processed_all_player_cards = []
    all_player_cards_data = state.get("all_player_cards", [])
    player_decisions_data = state.get("decisions", [])
    
    # Ensure player_decisions_data has an entry for every player
    full_player_decisions = list(player_decisions_data) + [""] * (len(state.get("players", [])) - len(player_decisions_data))

    user_idx_for_card_reveal = state["user_player_position_idx"] # Default to current position
    if state["game_phase"] == "showdown" and "user_player_position_idx_last_hand" in state:
        user_idx_for_card_reveal = state["user_player_position_idx_last_hand"]

    if all_player_cards_data and len(all_player_cards_data) == len(state.get("players", [])):
        for i, p_cards_list in enumerate(all_player_cards_data):
            player_decision_for_this_player = full_player_decisions[i]

            if not p_cards_list or len(p_cards_list) != 2:
                processed_all_player_cards.append(["back.png", "back.png"])
                continue

            can_see_cards = False
            # Rule 1: User's own cards
            if i == user_idx_for_card_reveal:
                if state["game_phase"] != "pre_deal": # Show if dealt
                    can_see_cards = True
            
            # Rule 2: Showdown specific visibility
            if state["game_phase"] == "showdown":
                if player_decision_for_this_player == "ALL_IN":
                    can_see_cards = True
                elif player_decision_for_this_player == "FOLD": # As requested, show folded cards at showdown
                    can_see_cards = True
                elif i in state.get("revealed_cards", {}): # Part of evaluated showdown
                    can_see_cards = True
                # If it's the user (i == user_idx_for_card_reveal), can_see_cards would likely be true already.

            if can_see_cards:
                processed_all_player_cards.append([
                    find_card_image_filename(p_cards_list[0]),
                    find_card_image_filename(p_cards_list[1])
                ])
            else:
                processed_all_player_cards.append(["back.png", "back.png"])
    else:
        for _ in state.get("players", []):
            processed_all_player_cards.append(["back.png", "back.png"])

    display_state["all_player_cards_display"] = processed_all_player_cards
    display_state["community_cards_display"] = []
    if state["game_phase"] == "showdown":
        display_state["community_cards_display"] = [find_card_image_filename(card_str) for card_str in state.get("community_cards", [])[:5]]
    
    display_state["user_hand_display"] = ["?", "?"]
    if all_player_cards_data and \
       len(all_player_cards_data) > state["user_player_position_idx"] and \
       all_player_cards_data[state["user_player_position_idx"]] and \
       len(all_player_cards_data[state["user_player_position_idx"]]) == 2 and \
       state["game_phase"] != "pre_deal":
        user_cards_now = all_player_cards_data[state["user_player_position_idx"]]
        display_state["user_hand_display"] = [user_cards_now[0], user_cards_now[1]]


    # Pass winner indices for highlighting
    display_state["winner_indices"] = []
    if state["game_phase"] == "showdown": # Only pass if it's showdown
        display_state["winner_indices"] = state.get("winners_player_indices", [])
        
    return jsonify(display_state)


@app.route('/deal', methods=['POST'])
def deal_cards_api():
    state = get_game_state()

    if state["game_phase"] == "awaiting_decision":
        log_message(state, "Cannot deal, hand in progress.")
        save_game_state(state)
        return jsonify({"success": False, "message": "Hand in progress."})

    # Reset stacks and pot for new hand
    state["player_stacks"] = [8.0, 8.0, 8.0, 8.0]  # Reset all stacks to starting amount
    state["pot_size"] = 0.0  # Reset pot size
    state["player_bets_this_hand"] = [0.0] * len(state["players"]) # Reset bets for the new hand


    state["hands_played"] += 1
    state["current_player_idx"] = state["user_player_position_idx"] # User is always the one to act on their turn
    state["decisions"] = [""] * len(state["players"]) # Reset decisions
    state["winner_info"] = None
    state["winners_player_indices"] = []
    state["revealed_cards"] = {}
    state["user_player_position_idx_last_hand"] = state["user_player_position_idx"] # Set for current hand

    deck = [(rank, suit) for rank in RANKS for suit in SUITS]
    random.shuffle(deck)

    state["all_player_cards"] = []
    for i in range(len(state["players"])):
        card1 = deck.pop(0)
        card2 = deck.pop(0)
        state["all_player_cards"].append([f"{card1[0]}{card1[1]}", f"{card2[0]}{card2[1]}"])

    state["community_cards"] = [f"{card[0]}{card[1]}" for card in deck[:5]] # Deal 5, reveal later

    # Blinds
    sb_idx = state["players"].index("SB")
    bb_idx = state["players"].index("BB")
    
    # SB post - Stacks are full (8.0) here
    state["player_stacks"][sb_idx] = round(state["player_stacks"][sb_idx] - state["small_blind"], 2)
    state["player_bets_this_hand"][sb_idx] = state["small_blind"]
    state["pot_size"] = round(state["pot_size"] + state["small_blind"], 2)
    
    # BB post - Stacks are full (8.0) here
    state["player_stacks"][bb_idx] = round(state["player_stacks"][bb_idx] - state["big_blind"], 2)
    state["player_bets_this_hand"][bb_idx] = state["big_blind"]
    state["pot_size"] = round(state["pot_size"] + state["big_blind"], 2)
    
    log_message(state, f"Hand #{state['hands_played']}. You are {state['players'][state['user_player_position_idx']]}.")
    user_cards = state["all_player_cards"][state["user_player_position_idx"]]
    log_message(state, f"Your hand: {user_cards[0]} {user_cards[1]}")

    # Simulate decisions for players before the user
    # This simplified model assumes user is 'current_player_idx' and others act based on that.
    # A more complex model would have a proper turn order.
    # For now, let's assume CO acts first, then BTN, then SB, then BB. User is one of them.
    
    # Determine who acts before the user in this round
    # Example: if user is SB (idx 2), CO (idx 0) and BTN (idx 1) act first.
    for i in range(state["user_player_position_idx"]):
        player_pos_name = state["players"][i]
        player_actual_cards = state["all_player_cards"][i]
        player_hand_str = format_hand_for_strategy(player_actual_cards)
        decision = simulate_optimal_decision(player_pos_name, player_hand_str, state)
        state["decisions"][i] = decision
        log_message(state, f"{player_pos_name} ({player_hand_str}) decided: {decision}")
        if decision == "ALL_IN":
            amount_to_add_to_bet = state["player_stacks"][i] # Their remaining stack
            state["pot_size"] = round(state["pot_size"] + amount_to_add_to_bet, 2)
            state["player_bets_this_hand"][i] += amount_to_add_to_bet # Add to existing bet (0 or blind)
            state["player_stacks"][i] = 0
        # If FOLD, player_bets_this_hand[i] remains as is (their blind, or 0).

    state["game_phase"] = "awaiting_decision"
    save_game_state(state)
    return jsonify({"success": True})


@app.route('/make_decision/<string:decision_type>', methods=['POST'])
def make_decision_api(decision_type):
    state = get_game_state()

    if state["game_phase"] != "awaiting_decision":
        return jsonify({"success": False, "message": "Not time for decision."})

    user_original_position_this_hand = state["user_player_position_idx"]
    state["decisions"][user_original_position_this_hand] = decision_type
    log_message(state, f"You ({state['players'][user_original_position_this_hand]}) decided: {decision_type}")

    # Update user's bet and stack for ALL_IN
    if decision_type == "ALL_IN":
        amount_to_add_to_pot = state["player_stacks"][user_original_position_this_hand]
        state["player_bets_this_hand"][user_original_position_this_hand] += amount_to_add_to_pot
        state["pot_size"] = round(state["pot_size"] + amount_to_add_to_pot, 2)
        state["player_stacks"][user_original_position_this_hand] = 0
        log_message(state, f"You go ALL IN. Your bet this hand: {state['player_bets_this_hand'][user_original_position_this_hand]:.2f} BB. Pot: {state['pot_size']:.2f} BB")


    # Simulate decisions for other players who haven't acted yet, using the optimal strategy.
    for i in range(len(state["players"])):
        if i == user_original_position_this_hand:
            continue # Skip user, decision already made

        if not state["decisions"][i]: # If no decision yet for this player
            player_pos_name = state["players"][i]
            
            # Ensure cards are available for decision making
            if not state["all_player_cards"] or i >= len(state["all_player_cards"]) or not state["all_player_cards"][i]:
                log_message(state, f"Warning: Cards not found for {player_pos_name}, defaulting their action to FOLD.")
                state["decisions"][i] = "FOLD" # Fallback if cards are missing
                continue

            player_actual_cards = state["all_player_cards"][i]
            player_hand_str = format_hand_for_strategy(player_actual_cards)
            
            # Call simulate_optimal_decision for opponents
            opponent_decision = simulate_optimal_decision(player_pos_name, player_hand_str, state)
            state["decisions"][i] = opponent_decision
            log_message(state, f"{state['players'][i]} ({player_hand_str}) decided: {opponent_decision}")

            if opponent_decision == "ALL_IN":
                # Amount to add is their current stack (if > 0)
                amount_opponent_adds_to_bet = state["player_stacks"][i]
                if amount_opponent_adds_to_bet > 0:
                    state["player_bets_this_hand"][i] += amount_opponent_adds_to_bet # Add to existing bet (e.g., blind)
                    state["pot_size"] = round(state["pot_size"] + amount_opponent_adds_to_bet, 2)
                    state["player_stacks"][i] = 0
                    log_message(state, f"{state['players'][i]} goes ALL IN. Their bet: {state['player_bets_this_hand'][i]:.2f} BB. Pot: {state['pot_size']:.2f} BB")
                else:
                    log_message(state, f"{state['players'][i]} is already all-in or has no chips to bet for ALL_IN decision.")
            # If FOLD, their stack and current bet (e.g. blind) remain. The decision is logged above.


    # Determine winner
    determine_winner(state, user_original_position_this_hand) # Pass user's original position
    state["game_phase"] = "showdown"
    
    state["user_player_position_idx_last_hand"] = user_original_position_this_hand # Store for get_state

    # Rotate positions for next hand (user moves to next position)
    # This rotation should happen AFTER the current hand is fully resolved and state saved for showdown
    # So, user_player_position_idx is rotated for the *next* deal.
    state["user_player_position_idx"] = (user_original_position_this_hand + 1) % len(state["players"])
    
    save_game_state(state)
    return jsonify({"success": True})

def determine_winner(state, user_idx_for_this_hand): # Added user_idx_for_this_hand
    # Ensure decisions array is properly initialized
    current_decisions = state.get("decisions", [])
    state["decisions"] = current_decisions + ["FOLD"] * (len(state["players"]) - len(current_decisions))
    for i in range(len(state["decisions"])):
        if not state["decisions"][i]: 
            state["decisions"][i] = "FOLD" # Default unmade decisions to FOLD

    # user_p_idx is the user's position for the hand just played
    user_contribution_this_hand = state["player_bets_this_hand"][user_idx_for_this_hand]
    current_cumulative_bb_val = state["player_cumulative_bb"][-1] if state["player_cumulative_bb"] else 0
    state["winners_player_indices"] = [] # Initialize/reset

    non_folded_players = [i for i, d in enumerate(state["decisions"]) if d != "FOLD"]

    if not non_folded_players:
        log_message(state, "Error: All players folded? Pot distributed or error.")
        final_user_bb_change_for_hand = -user_contribution_this_hand
        state["player_cumulative_bb"].append(current_cumulative_bb_val + final_user_bb_change_for_hand)
        log_message(state, f"Your BB change for hand: {final_user_bb_change_for_hand:.2f}. Total: {state['player_cumulative_bb'][-1]:.2f}")
        state["winner_info"] = {"name": "No Winner", "hand_type": "All Folded"}
        return

    if len(non_folded_players) == 1:
        winner_idx = non_folded_players[0]
        log_message(state, f"{state['players'][winner_idx]} wins the pot of {state['pot_size']:.2f} BB (others folded).")
        state["winner_info"] = {"name": state['players'][winner_idx], "hand_type": "Opponents Folded"}
        state["winners_player_indices"] = [winner_idx]
        if state["all_player_cards"] and len(state["all_player_cards"]) > winner_idx and state["all_player_cards"][winner_idx]:
            state["revealed_cards"][winner_idx] = state["all_player_cards"][winner_idx]
        
        state["player_stacks"][winner_idx] = round(state["player_stacks"][winner_idx] + state["pot_size"], 2)
        
        final_user_bb_change_for_hand = 0
        if winner_idx == user_idx_for_this_hand:
            final_user_bb_change_for_hand = state["pot_size"] - user_contribution_this_hand
        else:
            final_user_bb_change_for_hand = -user_contribution_this_hand
        
        state["player_cumulative_bb"].append(current_cumulative_bb_val + final_user_bb_change_for_hand)
        log_message(state, f"Your BB change for hand: {final_user_bb_change_for_hand:.2f}. Total: {state['player_cumulative_bb'][-1]:.2f}")
        return

    showdown_players_indices = non_folded_players 
    best_score = None
    winners_indices_local = [] # Use local variable for winners in this scope
    player_scores = {}

    for p_idx in showdown_players_indices:
        if not state["all_player_cards"] or p_idx >= len(state["all_player_cards"]) or not state["all_player_cards"][p_idx]:
            log_message(state, f"Error: Missing cards for player {state['players'][p_idx]} at index {p_idx} during showdown.")
            continue # Skip this player if cards are missing
        hole_cards = state["all_player_cards"][p_idx]
        score = evaluator.evaluate_hand(hole_cards, state["community_cards"])
        player_scores[p_idx] = score
        state["revealed_cards"][p_idx] = hole_cards

        if score:
            log_message(state, f"{state['players'][p_idx]} has {evaluator.hand_type_to_string(score[0])} ({hole_cards})")
            if best_score is None or score > best_score:
                best_score = score
                winners_indices_local = [p_idx]
            elif score == best_score:
                winners_indices_local.append(p_idx)
        else:
            log_message(state, f"{state['players'][p_idx]} ({hole_cards}) - could not evaluate hand.")

    state["winners_player_indices"] = winners_indices_local # Store in state

    if not winners_indices_local or not best_score:
        log_message(state, "Error: Could not determine a winner from hand evaluation.")
        final_user_bb_change_for_hand = -user_contribution_this_hand if user_idx_for_this_hand in showdown_players_indices else -user_contribution_this_hand
        state["player_cumulative_bb"].append(current_cumulative_bb_val + final_user_bb_change_for_hand)
        log_message(state, f"Your BB change for hand: {final_user_bb_change_for_hand:.2f}. Total: {state['player_cumulative_bb'][-1]:.2f}")
        state["winner_info"] = {"name": "Evaluation Error", "hand_type": "Unknown"}
        return

    pot_per_winner = round(state["pot_size"] / len(winners_indices_local), 2)
    winner_names = [state['players'][idx] for idx in winners_indices_local]
    hand_name = evaluator.hand_type_to_string(best_score[0])
    log_message(state, f"Winner(s): {', '.join(winner_names)} with {hand_name}. Each gets {pot_per_winner:.2f} BB.")
    state["winner_info"] = {"name": ', '.join(winner_names), "hand_type": hand_name}

    for w_idx in winners_indices_local:
        state["player_stacks"][w_idx] = round(state["player_stacks"][w_idx] + pot_per_winner, 2)

    final_user_bb_change_for_hand = 0
    if user_idx_for_this_hand in winners_indices_local:
        final_user_bb_change_for_hand = pot_per_winner - user_contribution_this_hand
    elif user_idx_for_this_hand in showdown_players_indices:
        final_user_bb_change_for_hand = -user_contribution_this_hand
    else: # User folded before showdown
        final_user_bb_change_for_hand = -user_contribution_this_hand
        
    state["player_cumulative_bb"].append(current_cumulative_bb_val + final_user_bb_change_for_hand)
    log_message(state, f"Your BB change for hand: {final_user_bb_change_for_hand:.2f}. Total: {state['player_cumulative_bb'][-1]:.2f}")


@app.route('/restart', methods=['POST'])
def restart_api():
    user_player_pos_idx = session.get('game_state', {}).get('user_player_position_idx', 0)
    session['game_state'] = get_initial_game_state()
    # Preserve user's position through restarts, or reset to CO
    session['game_state']['user_player_position_idx'] = 0 # Or user_player_pos_idx to keep it
    log_message(session['game_state'], "Game restarted!")
    save_game_state(session['game_state']) # Explicitly save after modifying
    return jsonify({"success": True})


if __name__ == '__main__':
    static_card_dir = os.path.join('static', 'card_images')
    if not os.path.exists(static_card_dir):
        os.makedirs(static_card_dir, exist_ok=True)
        print(f"Created {static_card_dir} directory. Please add card images there.")
    #app.run(debug=True) 
    app.run(host="0.0.0.0", port = 8080)
