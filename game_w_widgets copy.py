import pickle
import tkinter as tk
import time
import random
import numpy as np
import os

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
        # Rank-to-value mapping
        self.RANK_VALUES = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
            "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
        }
    
    def evaluate_hand(self, hole_cards, community_cards):
        all_cards = hole_cards + community_cards
        combinations = []
        self.generate_combinations(all_cards, 5, 0, [], combinations)
        
        best_score = None
        for combo in combinations:
            score = self.evaluate_five_card_hand(combo)
            if best_score is None or score > best_score:
                best_score = score
        
        return best_score
    
    def evaluate_five_card_hand(self, hand):
        # Convert string cards to values
        if isinstance(hand[0], str):
            card_values = [self.RANK_VALUES[c[:-1]] for c in hand]
        else:
            card_values = [self.RANK_VALUES[c.rank] for c in hand]
        
        card_values.sort(reverse=True)
        
        # Count frequencies of each value
        freq = {}
        for v in card_values:
            freq[v] = freq.get(v, 0) + 1
        
        # Sort by frequency (highest first), then by card value (highest first)
        freq_sorted = sorted(freq.items(), key=lambda x: (x[1], x[0]), reverse=True)
        
        # Check for flush and straight
        is_flush = self.check_flush(hand)
        straight_high = [0]  # Use list to pass by reference
        is_straight = self.check_straight(card_values, straight_high)
        
        if is_flush and is_straight:
            return [self.STRAIGHT_FLUSH, straight_high[0]]
        
        # Four of a kind
        if freq_sorted[0][1] == 4:
            kicker = next(v for v in card_values if v != freq_sorted[0][0])
            return [self.FOUR_KIND, freq_sorted[0][0], kicker]
        
        # Full house
        if freq_sorted[0][1] == 3 and freq_sorted[1][1] >= 2:
            return [self.FULL_HOUSE, freq_sorted[0][0], freq_sorted[1][0]]
        
        if is_flush:
            return [self.FLUSH] + card_values
        
        if is_straight:
            return [self.STRAIGHT, straight_high[0]]
        
        # Three of a kind
        if freq_sorted[0][1] == 3:
            kickers = [v for v in card_values if v != freq_sorted[0][0]]
            return [self.THREE_KIND, freq_sorted[0][0], kickers[0], kickers[1]]
        
        # Two pair
        if freq_sorted[0][1] == 2 and freq_sorted[1][1] == 2:
            kicker = next(v for v in card_values if v != freq_sorted[0][0] and v != freq_sorted[1][0])
            return [self.TWO_PAIR, freq_sorted[0][0], freq_sorted[1][0], kicker]
        
        # One pair
        if freq_sorted[0][1] == 2:
            kickers = [v for v in card_values if v != freq_sorted[0][0]]
            return [self.PAIR, freq_sorted[0][0], kickers[0], kickers[1], kickers[2]]
        
        # High card
        return [self.HIGH_CARD] + card_values
    
    def generate_combinations(self, cards, combination_size, start, current_combo, all_combinations):
        if len(current_combo) == combination_size:
            all_combinations.append(current_combo[:])
            return
        
        for i in range(start, len(cards) - (combination_size - len(current_combo)) + 1):
            current_combo.append(cards[i])
            self.generate_combinations(cards, combination_size, i + 1, current_combo, all_combinations)
            current_combo.pop()
    
    def check_flush(self, hand):
        if isinstance(hand[0], str):
            # Extract suit properly - the last character for all cards
            # For cards like "10h", the suit is still the last character
            suit = hand[0][-1]
            return all(c[-1] == suit for c in hand)
        else:
            suit = hand[0].suit
            return all(c.suit == suit for c in hand)
    
    def check_straight(self, values, high_straight_value):
        sorted_values = sorted(values)
        
        # Check for normal straight
        if sorted_values[4] - sorted_values[0] == 4:
            for i in range(4):
                if sorted_values[i+1] - sorted_values[i] != 1:
                    return False
            high_straight_value[0] = sorted_values[4]
            return True
        
        # Check for A-5 straight (wheel)
        if sorted_values == [2, 3, 4, 5, 14]:
            high_straight_value[0] = 5
            return True
        
        return False

class PokerGameApp:
    def __init__(self, root, hand_data):
        self.root = root
        self.root.title("Poker Game with Position Switching")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.hand_data = hand_data
        self.players = ["CO","BTN","SB","BB"]
        self.player_wins = {player: 0 for player in self.players}
        self.current_player_index = 0
        self.hands_played = 0
        self.current_hand = None
        self.community_cards = []
        self.decisions = []
        self.player_stacks = [8.0, 8.0, 8.0, 8.0]  # Starting stacks in BB
        self.all_player_cards = []  # To store all players' cards
        self.evaluator = PokerEvaluator()  # Initialize the poker hand evaluator
        
        # Track player's cumulative BB won/lost
        self.player_cumulative_bb = [0]  # Start with 0
        
        # Define pot sizes and blinds
        self.small_blind = 0.4  # in BB
        self.big_blind = 1.0    # in BB
        
        # Card images dictionary
        self.card_images = {}
        self.card_back_image = None
        
        # Create main frame for better organization
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Define log_message method as a no-op function
        def _log_message(message):
            # Just print to console instead of displaying in UI
            print(message)
        
        # Assign the local function to self.log_message
        self.log_message = _log_message
        
        # Card ranks and suits
        self.ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
        self.suits = ['h', 'd', 'c', 's']
        
        # Import matplotlib for plotting
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            self.matplotlib_available = True
        except ImportError:
            self.log_message("Matplotlib not available. Performance graph disabled.")
            self.matplotlib_available = False
        
        # Load card images
        self.load_card_images()
        
        # Create poker table canvas
        self.table_frame = tk.Frame(self.main_frame)
        self.table_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.table_canvas = tk.Canvas(self.table_frame, width=600, height=400, bg="green")
        self.table_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw poker table
        self.draw_poker_table()
        
        # Button frame for decision buttons
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(pady=5)

        # Buttons for decisions
        self.button_all_in = tk.Button(self.button_frame, text="ALL_IN", command=lambda: self.record_decision("ALL_IN"))
        self.button_all_in.pack(side=tk.LEFT, padx=5)

        self.button_fold = tk.Button(self.button_frame, text="FOLD", command=lambda: self.record_decision("FOLD"))
        self.button_fold.pack(side=tk.LEFT, padx=5)

        # Deal button
        self.deal_button = tk.Button(self.button_frame, text="Deal New Hand", command=self.deal_cards)
        self.deal_button.pack(side=tk.LEFT, padx=5)

        # Restart button (always visible)
        self.restart_button = tk.Button(self.button_frame, text="Restart Game", command=self.restart_game)
        self.restart_button.pack(side=tk.LEFT, padx=5)

        # Add counter display frame
        self.counter_frame = tk.Frame(self.main_frame)
        self.counter_frame.pack(pady=5)
        
        # Hands played counter
        self.counter_label = tk.Label(self.counter_frame, text="Hands played: 0", font=("Arial", 12))
        self.counter_label.pack()

        # Add performance graph frame
        if self.matplotlib_available:
            self.graph_frame = tk.Frame(self.main_frame)
            self.graph_frame.pack(pady=10, fill=tk.BOTH, expand=True)
            
            # Create the initial plot
            self.fig, self.ax = plt.subplots(figsize=(8, 3))
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Initialize the plot
            self.update_performance_graph()

        # Initially disable the decision buttons until cards are dealt
        self.button_all_in.config(state=tk.DISABLED)
        self.button_fold.config(state=tk.DISABLED)
        
        # Initial message
        self.log_message("Game started! Click 'Deal New Hand' to begin.")

    def load_card_images(self):
        """Load card images from the card_images directory."""
        try:
            from PIL import Image, ImageTk
            
            # Define card dimensions
            card_width = 60
            card_height = 80
            
            # Load card back image
            try:
                card_back = Image.open("card_images/back.png")
                card_back = card_back.resize((card_width, card_height), Image.LANCZOS)
                self.card_back_image = ImageTk.PhotoImage(card_back)
            except:
                self.log_message("Warning: Could not load card back image. Using placeholder.")
                self.card_back_image = None
            
            # Load all card images
            for rank in self.ranks:
                for suit in self.suits:
                    card_name = f"{rank}{suit}"
                    try:
                        # Try to load the image file
                        img_path = f"card_images/{card_name}.png"
                        if not os.path.exists(img_path):
                            # Try alternative naming (e.g., "As.png" instead of "As.png")
                            img_path = f"card_images/{rank.lower()}{suit}.png"
                            if not os.path.exists(img_path):
                                raise FileNotFoundError
                                
                        card_img = Image.open(img_path)
                        card_img = card_img.resize((card_width, card_height), Image.LANCZOS)
                        self.card_images[card_name] = ImageTk.PhotoImage(card_img)
                    except:
                        self.log_message(f"Warning: Could not load image for {card_name}. Using placeholder.")
                        self.card_images[card_name] = None
        except ImportError:
            self.log_message("PIL not available. Card images disabled.")
            self.card_back_image = None
    
    def draw_poker_table(self):
        """Draw the poker table with player positions."""
        canvas_width = 600
        canvas_height = 400
        
        # Scale down all elements to ensure they fit within the canvas
        scale_factor = 0.85  # Reduce size of all elements by 15%
        
        # Center the table in the canvas
        table_width = canvas_width * scale_factor
        table_height = canvas_height * scale_factor
        h_offset = (canvas_width - table_width) / 2
        v_offset = (canvas_height - table_height) / 2
        
        # Draw table (green oval) - scaled down and centered
        self.table_canvas.create_oval(
            h_offset + 50, v_offset + 50, 
            canvas_width - h_offset - 50, canvas_height - v_offset - 50, 
            fill="darkgreen", outline="brown", width=10, tags="table"
        )
        
        # Draw center pot area
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        pot_radius = 40 * scale_factor
        self.table_canvas.create_oval(
            center_x - pot_radius, center_y - pot_radius,
            center_x + pot_radius, center_y + pot_radius,
            fill="green", outline="white", width=2, tags="pot_area"
        )
        
        # Pot text
        self.pot_text = self.table_canvas.create_text(
            center_x, center_y, 
            text="Pot: 0 BB", fill="white", 
            font=("Arial", 12, "bold"), tags="pot_text"
        )
        
        # Define player positions (clockwise: CO, BTN, SB, BB)
        # Position players in a smaller circle to ensure cards fit
        radius = min(table_width, table_height) * 0.2  # Smaller radius for player circle
        self.player_positions = [
            (center_x, center_y - radius),                # CO (top)
            (center_x + radius, center_y),                # BTN (right)
            (center_x, center_y + radius),                # SB (bottom)
            (center_x - radius, center_y)                 # BB (left)
        ]
        
        # Draw player positions and labels
        for i, (x, y) in enumerate(self.player_positions):
            # Player circle
            player_color = "gold" if i == self.current_player_index else "gray"
            self.table_canvas.create_oval(
                x-25, y-25, x+25, y+25, 
                fill=player_color, outline="white", 
                width=2, tags=f"player{i}_circle"
            )
            
            # Player label
            self.table_canvas.create_text(
                x, y, text=self.players[i], 
                fill="black", font=("Arial", 12, "bold"), 
                tags=f"player{i}_label"
            )
            
            # Player stack
            self.table_canvas.create_text(
                x, y+35, 
                text=f"{self.player_stacks[i]} BB", 
                fill="white", font=("Arial", 10), 
                tags=f"player{i}_stack"
            )
            
            # Card placeholders (face down initially)
            card_spacing = 25  # Reduced spacing between cards
            card_width = 50 * scale_factor  # Smaller cards
            card_height = 70 * scale_factor
            
            # Calculate card positions with better spacing
            # Move cards closer to player circles but ensure they don't overlap
            card_distance = 60 * scale_factor  # Distance from player circle to cards
            
            if i == 0:  # CO (top)
                card_x, card_y = x-card_spacing/2, y-card_distance
                card_anchor = tk.S
            elif i == 1:  # BTN (right)
                card_x, card_y = x+card_distance, y-card_spacing/2
                card_anchor = tk.W
            elif i == 2:  # SB (bottom)
                card_x, card_y = x-card_spacing/2, y+card_distance
                card_anchor = tk.N
            else:  # BB (left)
                card_x, card_y = x-card_distance, y-card_spacing/2
                card_anchor = tk.E
            
            # Create card placeholders
            for j in range(2):
                if i == 0:  # CO (top)
                    card_pos_x = card_x + (j * card_spacing)
                    card_pos_y = card_y
                elif i == 1:  # BTN (right)
                    card_pos_x = card_x
                    card_pos_y = card_y + (j * card_spacing)
                elif i == 2:  # SB (bottom)
                    card_pos_x = card_x + (j * card_spacing)
                    card_pos_y = card_y
                else:  # BB (left)
                    card_pos_x = card_x
                    card_pos_y = card_y + (j * card_spacing)
                
                # Create card placeholder
                if self.card_back_image:
                    self.table_canvas.create_image(
                        card_pos_x, card_pos_y, 
                        image=self.card_back_image, 
                        anchor=card_anchor, 
                        tags=f"player{i}_card{j+1}"
                    )
                else:
                    # Fallback if image loading failed
                    self.table_canvas.create_rectangle(
                        card_pos_x-20, card_pos_y-30, 
                        card_pos_x+20, card_pos_y+30, 
                        fill="white", outline="black", 
                        tags=f"player{i}_card{j+1}"
                    )
                    self.table_canvas.create_text(
                        card_pos_x, card_pos_y, 
                        text="?", fill="black", 
                        font=("Arial", 16, "bold"), 
                        tags=f"player{i}_card{j+1}_text"
                    )
        
        # Community cards area (center of table)
        self.community_card_positions = []
        comm_card_y = center_y + (radius * 0.5)  # Position community cards between center and bottom
        
        # Calculate total width of community cards to center them
        total_comm_cards = 5
        comm_card_spacing = 45 * scale_factor  # Reduced spacing
        total_width = (total_comm_cards - 1) * comm_card_spacing
        start_x = center_x - (total_width / 2)
        
        for i in range(5):
            x_pos = start_x + (i * comm_card_spacing)
            self.community_card_positions.append((x_pos, comm_card_y))
            
            # Create placeholder for community card
            if self.card_back_image:
                self.table_canvas.create_image(
                    x_pos, comm_card_y, 
                    image=self.card_back_image, 
                    tags=f"community_card{i+1}"
                )
            else:
                # Fallback if image loading failed
                self.table_canvas.create_rectangle(
                    x_pos-20, comm_card_y-30, 
                    x_pos+20, comm_card_y+30, 
                    fill="white", outline="black", 
                    tags=f"community_card{i+1}"
                )
                self.table_canvas.create_text(
                    x_pos, comm_card_y, 
                    text="?", fill="black", 
                    font=("Arial", 16, "bold"), 
                    tags=f"community_card{i+1}_text"
                )
            
            # Hide community cards initially
            self.table_canvas.itemconfig(f"community_card{i+1}", state=tk.HIDDEN)
    
    def update_table_display(self):
        """Update the poker table display based on current game state."""
        # Update player positions (highlight current player)
        for i in range(len(self.players)):
            player_color = "gold" if i == self.current_player_index else "gray"
            self.table_canvas.itemconfig(f"player{i}_circle", fill=player_color)
            
            # Update player stack display
            self.table_canvas.itemconfig(f"player{i}_stack", text=f"{self.player_stacks[i]} BB")
        
        # Hide all cards initially
        for i in range(len(self.players)):
            for j in range(2):
                if self.card_back_image:
                    self.table_canvas.itemconfig(f"player{i}_card{j+1}", image=self.card_back_image)
                else:
                    self.table_canvas.itemconfig(f"player{i}_card{j+1}_text", text="?")
        
        # Hide community cards
        for i in range(5):
            self.table_canvas.itemconfig(f"community_card{i+1}", state=tk.HIDDEN)
        
        # Clear any existing decision texts
        for i in range(len(self.players)):
            self.table_canvas.delete(f"player{i}_decision")
    
    def deal_cards(self):
        """Deal random cards to all players and enable decision buttons."""
        # Create a deck
        deck = [(rank, suit) for rank in self.ranks for suit in self.suits]
        random.shuffle(deck)
        
        # Deal 2 cards to each player
        self.all_player_cards = []
        for i in range(4):  # 4 players
            player_cards = [f"{deck[i*2][0]}{deck[i*2][1]}", f"{deck[i*2+1][0]}{deck[i*2+1][1]}"]
            self.all_player_cards.append(player_cards)
        
        # Remove dealt cards from deck
        deck = deck[8:]  # Remove first 8 cards (2 for each player)
        
        # Deal 5 community cards
        self.community_cards = [f"{card[0]}{card[1]}" for card in deck[:5]]
        
        # Update table display
        self.update_table_display()
        
        # Show current player's cards
        for j in range(2):
            card_value = self.all_player_cards[self.current_player_index][j]
            if card_value in self.card_images and self.card_images[card_value] is not None:
                self.table_canvas.itemconfig(
                    f"player{self.current_player_index}_card{j+1}", 
                    image=self.card_images[card_value]
                )
            else:
                # Fallback if image not available
                if not self.card_back_image:
                    self.table_canvas.itemconfig(
                        f"player{self.current_player_index}_card{j+1}_text", 
                        text=card_value
                    )
        
        # Format hand string for strategy lookup
        your_cards = self.all_player_cards[self.current_player_index]
        card1 = your_cards[0][:-1]  # Remove suit
        card2 = your_cards[1][:-1]  # Remove suit
        suited = your_cards[0][-1] == your_cards[1][-1]  # Check if same suit
        
        # Order cards by rank (higher rank first)
        rank_values = {rank: i for i, rank in enumerate(self.ranks)}
        if rank_values.get(card1, 0) < rank_values.get(card2, 0):
            first, second = card2, card1
        else:
            first, second = card1, card2
            
        self.current_hand = f"{first} {second}{'s' if suited else 'o'}"
        
        self.log_message(f"Your position: {self.players[self.current_player_index]}")
        self.log_message(f"Your hand: {your_cards[0]} {your_cards[1]} ({self.current_hand})")
        
        # Simulate decisions for players who act before the current player
        self.decisions = []
        if self.current_player_index > 0:  # If not the first player to act (CO)
            self.log_message("Previous players' decisions:")
            for i in range(self.current_player_index):
                player_index = i
                player = self.players[player_index]
                
                # Get this player's cards
                player_cards = self.all_player_cards[player_index]
                
                # Format hand for strategy lookup
                card1 = player_cards[0][:-1]  # Remove suit
                card2 = player_cards[1][:-1]  # Remove suit
                suited = player_cards[0][-1] == player_cards[1][-1]  # Check if same suit
                
                # Order cards by rank (higher rank first)
                if rank_values.get(card1, 0) < rank_values.get(card2, 0):
                    first, second = card2, card1
                else:
                    first, second = card1, card2
                    
                player_hand = f"{first} {second}{'s' if suited else 'o'}"
                
                # Simulate optimal decision
                optimal_decision = self.simulate_optimal_decision(player, player_hand)
                self.decisions.append(optimal_decision)
                self.log_message(f"{player} decided to {optimal_decision}")
                
                # Display decision on the table
                self.display_player_decision(player_index, optimal_decision)
        
        self.log_message(f"Community cards will be revealed after all decisions.")
        
        # Enable decision buttons
        self.button_all_in.config(state=tk.NORMAL)
        self.button_fold.config(state=tk.NORMAL)
        self.deal_button.config(state=tk.DISABLED)

    def display_player_decision(self, player_index, decision):
        """Display a player's decision on the table."""
        x, y = self.player_positions[player_index]
        
        # Remove any existing decision text
        self.table_canvas.delete(f"player{player_index}_decision")
        
        # Create decision text
        decision_color = "red" if decision == "FOLD" else "white"
        self.table_canvas.create_text(
            x, y+60, 
            text=decision, 
            fill=decision_color, 
            font=("Arial", 12, "bold"), 
            tags=f"player{player_index}_decision"
        )

    def record_decision(self, decision):
        """Record player's decision and simulate other players."""
        # Display the current player's decision
        self.display_player_decision(self.current_player_index, decision)
        
        # Check if you're BB and everyone folded before you
        if self.players[self.current_player_index] == "BB":
            # Check if all previous players folded
            all_folded = True
            for i in range(self.current_player_index):
                if i < len(self.decisions) and self.decisions[i] != "FOLD":
                    all_folded = False
                    break
            
            if all_folded:
                self.log_message(f"You (BB) win automatically (everyone folded)!")
                # Mark as auto-win for BB
                self.decisions = ["FOLD", "FOLD", "FOLD", "AUTO_WIN_BB"]
                
                # Reveal community cards
                self.reveal_community_cards()
                
                # Determine winner and update stacks
                self.determine_winner()
                
                # Update performance graph
                if self.matplotlib_available:
                    self.update_performance_graph()
                
                # Disable decision buttons
                self.button_all_in.config(state=tk.DISABLED)
                self.button_fold.config(state=tk.DISABLED)
                self.deal_button.config(state=tk.NORMAL)
                
                # Update player position for next hand
                self.current_player_index = (self.current_player_index + 1) % len(self.players)
                
                # Update hands played counter
                self.hands_played += 1
                self.counter_label.config(text=f"Hands played: {self.hands_played}")
                
                return
        
        # Record the player's decision
        self.decisions.append(decision)
        self.log_message(f"You ({self.players[self.current_player_index]}) decided to {decision}")
        
        # Simulate decisions for other players based on optimal strategy
        # Only simulate players who haven't acted yet
        if self.current_player_index < len(self.players) - 1:
            # Check if all previous players folded and next player is BB
            if self.players[self.current_player_index + 1] == "BB" and all(d == "FOLD" for d in self.decisions):
                # BB automatically wins if everyone folded
                bb_player = self.players[self.current_player_index + 1]
                bb_index = self.current_player_index + 1
                bb_cards = self.all_player_cards[bb_index]
                self.log_message(f"{bb_player} ({bb_cards[0]} {bb_cards[1]}) wins automatically (everyone folded)")
                self.decisions.append("AUTO_WIN")  # Special marker for BB auto-win
                
                # Display decision on the table
                self.display_player_decision(bb_index, "AUTO_WIN")
            else:
                # Simulate remaining players normally
                for i in range(self.current_player_index + 1, len(self.players)):
                    player_index = i
                    player = self.players[player_index]
                    
                    # Get this player's cards
                    player_cards = self.all_player_cards[player_index]
                    
                    # Format hand for strategy lookup
                    card1 = player_cards[0][:-1]  # Remove suit
                    card2 = player_cards[1][:-1]  # Remove suit
                    suited = player_cards[0][-1] == player_cards[1][-1]  # Check if same suit
                    
                    # Order cards by rank (higher rank first)
                    rank_values = {rank: i for i, rank in enumerate(self.ranks)}
                    if rank_values.get(card1, 0) < rank_values.get(card2, 0):
                        first, second = card2, card1
                    else:
                        first, second = card1, card2
                        
                    player_hand = f"{first} {second}{'s' if suited else 'o'}"
                    
                    # Check if everyone before this player folded and this player is BB
                    if player == "BB" and all(d == "FOLD" for d in self.decisions):
                        # BB automatically wins if everyone folded
                        self.log_message(f"{player} ({player_cards[0]} {player_cards[1]}) wins automatically (everyone folded)")
                        self.decisions.append("AUTO_WIN")  # Special marker for BB auto-win
                        
                        # Display decision on the table
                        self.display_player_decision(player_index, "AUTO_WIN")
                        break
                    else:
                        # Simulate optimal decision
                        optimal_decision = self.simulate_optimal_decision(player, player_hand)
                        self.decisions.append(optimal_decision)
                        self.log_message(f"{player} ({player_cards[0]} {player_cards[1]}) decided to {optimal_decision}")
                        
                        # Display decision on the table
                        self.display_player_decision(player_index, optimal_decision)
        
        # Reveal community cards
        self.reveal_community_cards()
        
        # Reveal all player cards
        self.reveal_all_player_cards()
        
        # Determine winner and update stacks
        self.determine_winner()
        
        # Update performance graph
        if self.matplotlib_available:
            self.update_performance_graph()
        
        # Disable decision buttons
        self.button_all_in.config(state=tk.DISABLED)
        self.button_fold.config(state=tk.DISABLED)
        self.deal_button.config(state=tk.NORMAL)
        
        # Update player position for next hand
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        # Update hands played counter
        self.hands_played += 1
        self.counter_label.config(text=f"Hands played: {self.hands_played}")

    def reveal_community_cards(self):
        """Reveal the community cards on the table."""
        self.log_message("Community cards: " + " ".join(self.community_cards))
        
        # Show each community card
        for i, card in enumerate(self.community_cards):
            self.table_canvas.itemconfig(f"community_card{i+1}", state=tk.NORMAL)
            
            if card in self.card_images and self.card_images[card] is not None:
                self.table_canvas.itemconfig(
                    f"community_card{i+1}", 
                    image=self.card_images[card]
                )
            else:
                # Fallback if image not available
                if not self.card_back_image:
                    self.table_canvas.itemconfig(
                        f"community_card{i+1}_text", 
                        text=card
                    )

    def reveal_all_player_cards(self):
        """Reveal all players' cards on the table."""
        for i, player_cards in enumerate(self.all_player_cards):
            for j, card in enumerate(player_cards):
                if card in self.card_images and self.card_images[card] is not None:
                    self.table_canvas.itemconfig(
                        f"player{i}_card{j+1}", 
                        image=self.card_images[card]
                    )
                else:
                    # Fallback if image not available
                    if not self.card_back_image:
                        self.table_canvas.itemconfig(
                            f"player{i}_card{j+1}_text", 
                            text=card
                        )

    def simulate_optimal_decision(self, player, player_hand):
        """Simulate a decision based on the optimal strategy from aggregated_results.pkl."""
        try:
            # Get initial infoset based on position
            initial_infoset = "P2:[P0:P][P1:P]"  # Example infoset
            
            # Try to get probabilities from hand_data
            fold_prob, all_in_prob = self.hand_data.get((initial_infoset, player_hand), (0.5, 0.5))
            
            # Make decision based on probabilities
            if random.random() < fold_prob:
                return "FOLD"
            else:
                return "ALL_IN"
        except:
            # Fallback to random decision if strategy lookup fails
            return random.choice(["ALL_IN", "FOLD"])

    def determine_winner(self):
        """Determine the winner of the hand and update player stacks."""
        try:
            # Fixed positions for players
            sb_position = 2  # SB is at index 2
            bb_position = 3  # BB is at index 3
            co_position = 0  # CO is at index 0
            btn_position = 1  # BTN is at index 1

            # Initialize pot contributions with blinds
            contributions = [0] * len(self.players)
            contributions[sb_position] = self.small_blind
            contributions[bb_position] = self.big_blind
            
            # Process decisions to update contributions
            for i, decision in enumerate(self.decisions):
                if i >= len(self.players):
                    break  # Avoid index out of range
                
                if decision == "ALL_IN":
                    # When a player goes all-in, they contribute their full stack
                    # This should override any blind contributions already made
                    contributions[i] = self.player_stacks[i]
            
            # Calculate total pot
            pot_size = sum(contributions)
            
            # Update pot display on table
            self.table_canvas.itemconfig(self.pot_text, text=f"Pot: {pot_size} BB")
            
            # Log contributions for debugging
            self.log_message(f"Pot contributions: {[f'{self.players[i]}: {c}' for i, c in enumerate(contributions)]}")
            
            # Check for BB auto-win (everyone folded)
            if "AUTO_WIN" in self.decisions or "AUTO_WIN_BB" in self.decisions:
                winner = bb_position
                self.log_message(f"{self.players[winner]} wins the pot (everyone folded)!")
                
                # Highlight the winner
                self.highlight_winner(winner)
                
                # Calculate pot size
                net_win = pot_size - contributions[bb_position]
                
                # Update player's cumulative BB
                if winner == self.current_player_index:
                    # Won the pot minus our contribution
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] + net_win)
                    # Update win counter only for the current player
                    self.player_wins[self.players[winner]] += net_win
                else:
                    # Lost our contribution to the pot
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] - contributions[self.current_player_index])
                
                return
            
            # Count active players (those who didn't fold)
            active_players = []
            for i, decision in enumerate(self.decisions):
                if decision != "FOLD":
                    active_players.append(i)
            
            # If everyone folded except one player, they win automatically
            if len(active_players) == 1 and len(self.decisions) == len(self.players):
                winner = active_players[0]
                self.log_message(f"{self.players[winner]} wins the pot!")
                
                # Highlight the winner
                self.highlight_winner(winner)
                
                net_win = pot_size - contributions[winner]
                
                # Update player's cumulative BB
                if winner == self.current_player_index:
                    # Won the pot minus our contribution
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] + net_win)
                    # Update win counter only for the current player
                    self.player_wins[self.players[winner]] += net_win
                else:
                    # Lost our contribution to the pot
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] - contributions[self.current_player_index])
                
                return                
            
            # If multiple players are active, evaluate hands
            best_score = None
            winners = []
            
            for player_index in active_players:
                # Get player's hole cards
                hole_cards = self.all_player_cards[player_index]
                # Evaluate hand
                score = self.evaluator.evaluate_hand(hole_cards, self.community_cards)
                
                if score is not None:
                    self.log_message(f"{self.players[player_index]}'s hand score: {self.hand_type_to_string(score[0])}")
                    
                    if best_score is None or score > best_score:
                        best_score = score
                        winners = [player_index]
                    elif score == best_score:
                        winners.append(player_index)
            
            # Announce winner(s)
            if not winners or best_score is None:
                self.log_message("Error: Could not determine a winner.")
                # Still add a data point to keep graph consistent
                self.player_cumulative_bb.append(self.player_cumulative_bb[-1])
                return
            
            if len(winners) == 1:
                winner = winners[0]
                self.log_message(f"{self.players[winner]} wins with {self.hand_type_to_string(best_score[0])}!")
                
                # Highlight the winner
                self.highlight_winner(winner)
                
                net_win = pot_size - contributions[winner]
                
                # Update player's cumulative BB
                if winner == self.current_player_index:
                    # Won the pot minus our contribution
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] + net_win)
                    # Update win counter only for the current player
                    self.player_wins[self.players[winner]] += net_win
                else:
                    # Lost our contribution to the pot
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] - contributions[self.current_player_index])
            else:
                winner_names = [self.players[idx] for idx in winners]
                self.log_message(f"Split pot between {', '.join(winner_names)} with {self.hand_type_to_string(best_score[0])}!")
                
                # Highlight all winners
                for winner in winners:
                    self.highlight_winner(winner)
                
                # Calculate split pot amount per winner
                split_amount = pot_size / len(winners)
                
                # Check if current player is among winners
                if self.current_player_index in winners:
                    # Won split amount minus our contribution
                    net_win = split_amount - contributions[self.current_player_index]
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] + net_win)
                    # Update win counter only for the current player
                    self.player_wins[self.players[self.current_player_index]] += net_win
                else:
                    # Lost our contribution to the pot
                    self.player_cumulative_bb.append(self.player_cumulative_bb[-1] - contributions[self.current_player_index])
            
            # Log the BB change for clarity
            last_bb = self.player_cumulative_bb[-2] if len(self.player_cumulative_bb) > 1 else 0
            current_bb = self.player_cumulative_bb[-1]
            bb_change = current_bb - last_bb
            self.log_message(f"Your BB change: {bb_change:.2f} BB (Total: {current_bb:.2f} BB)")
            
        except Exception as e:
            # Catch any exceptions and log them
            self.log_message(f"Error determining winner: {str(e)}")
            import traceback
            # Still add a data point to keep graph consistent
            self.player_cumulative_bb.append(self.player_cumulative_bb[-1])

    def hand_type_to_string(self, hand_type):
        """Convert hand type value to readable string."""
        hand_types = {
            0: "High Card",
            1: "Pair",
            2: "Two Pair",
            3: "Three of a Kind",
            4: "Straight",
            5: "Flush",
            6: "Full House",
            7: "Four of a Kind",
            8: "Straight Flush"
        }
        return hand_types.get(hand_type, "Unknown Hand")

    def update_performance_graph(self):
        """Update the performance graph with current cumulative BB data."""
        if not self.matplotlib_available:
            return
            
        try:
            # Clear the previous plot
            self.ax.clear()
            
            # Plot the cumulative BB
            x = range(len(self.player_cumulative_bb))
            self.ax.plot(x, self.player_cumulative_bb, 'b-', linewidth=2)
            
            # Add a horizontal line at y=0
            self.ax.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            
            # Set labels and title
            self.ax.set_xlabel('Hands Played')
            self.ax.set_ylabel('Cumulative BB Won/Lost')
            self.ax.set_title('Your Performance in Big Blinds')
            
            # Dynamically adjust y-axis limits based on data
            if len(self.player_cumulative_bb) > 1:
                min_val = min(self.player_cumulative_bb)
                max_val = max(self.player_cumulative_bb)
                range_val = max(1, max_val - min_val)  # Ensure at least range of 1
                
                # Add some padding to the limits
                self.ax.set_ylim(min_val - range_val * 0.1, max_val + range_val * 0.1)
            
            # Add grid
            self.ax.grid(True, linestyle='--', alpha=0.7)
            
            # Update the canvas
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            self.log_message(f"Error updating performance graph: {str(e)}")

    def restart_game(self):
        """Resets the game and logs a restart message."""
        self.log_message("Game restarted! Click 'Deal New Hand' to begin.")
        
        # Reset game state
        self.decisions = []
        self.community_cards = []
        self.all_player_cards = []
        self.current_player_index = 0
        self.hands_played = 0
        self.counter_label.config(text=f"Hands played: {self.hands_played}")
        
        # Reset win counters
        for player in self.players:
            self.player_wins[player] = 0
        
        # Reset cumulative BB and update graph
        self.player_cumulative_bb = [0]
        if self.matplotlib_available:
            self.update_performance_graph()
        
        # Update table display
        self.update_table_display()
        
        # Enable/disable appropriate buttons
        self.button_all_in.config(state=tk.DISABLED)
        self.button_fold.config(state=tk.DISABLED)
        self.deal_button.config(state=tk.NORMAL)

    def on_closing(self):
        """Handle window close event by terminating the application"""
        self.root.destroy()
        import sys
        sys.exit(0)

    def highlight_winner(self, player_index):
        """Highlight the winning player and reveal their cards."""
        # Reveal the player's cards
        for j in range(2):
            card_tag = f"player{player_index}_card{j+1}"
            card_value = self.all_player_cards[player_index][j]
            if card_value in self.card_images and self.card_images[card_value] is not None:
                self.table_canvas.itemconfig(card_tag, image=self.card_images[card_value])
        
        # Create a highlight effect around the player
        x, y = self.player_positions[player_index]
        highlight = self.table_canvas.create_oval(
            x-50, y-50, x+50, y+50, 
            outline="gold", width=3, 
            tags=f"highlight_{player_index}"
        )
        
        # Animate the highlight (blink effect)
        def blink_highlight(count=0):
            if count < 6:  # Blink 3 times
                visible = count % 2 == 0
                self.table_canvas.itemconfig(highlight, state=tk.NORMAL if visible else tk.HIDDEN)
                self.root.after(300, lambda: blink_highlight(count+1))
            else:
                self.table_canvas.delete(highlight)
        
        blink_highlight()

    def calculate_player_contributions(self):
        """Calculate how much each player contributed to the pot."""
        # Fixed positions for players
        sb_position = 2  # SB is at index 2
        bb_position = 3  # BB is at index 3
        
        # Initialize pot contributions
        contributions = [0] * len(self.players)
        
        # Add blinds
        contributions[sb_position] = self.small_blind
        contributions[bb_position] = self.big_blind
        
        # Process decisions
        for i, decision in enumerate(self.decisions):
            if decision == "ALL_IN":
                # Player goes all-in with their stack
                contributions[i] = self.player_stacks[i]
        
        return contributions

    def update_cumulative_bb(self, winner, pot_size):
        """Update the cumulative BB for the current player based on the hand result."""
        contributions = self.calculate_player_contributions()
        
        if winner == self.current_player_index:
            # Current player won - add pot minus their contribution
            net_win = pot_size - contributions[self.current_player_index]
            self.player_cumulative_bb.append(self.player_cumulative_bb[-1] + net_win)
        else:
            # Current player lost - subtract their contribution
            self.player_cumulative_bb.append(self.player_cumulative_bb[-1] - contributions[self.current_player_index])

    def prepare_for_next_hand(self):
        """Prepare the interface for the next hand."""
        # Enable deal button
        self.deal_button.config(state=tk.NORMAL)
        
        # Update player position for next hand
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.label.config(text=f"You are {self.players[self.current_player_index]}")
        
        # Update hands played counter
        self.hands_played += 1
        self.counter_label.config(text=f"Hands played: {self.hands_played}")
        
        # Clear decisions
        self.decisions = []

def load_results():
    try:
        with open('aggregated_results.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print("Warning: aggregated_results.pkl not found. Using empty dictionary.")
        return {}

if __name__ == '__main__':
    # Try to create card_images directory if it doesn't exist
    try:
        if not os.path.exists("card_images"):
            os.makedirs("card_images")
            print("Created card_images directory. Please add card images to this folder.")
    except:
        pass
        
    hand_data_final = load_results()
    root = tk.Tk()
    app = PokerGameApp(root, hand_data_final)
    root.mainloop()
