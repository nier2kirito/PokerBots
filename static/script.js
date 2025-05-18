document.addEventListener('DOMContentLoaded', () => {
    const dealButton = document.getElementById('deal-button');
    const allInButton = document.getElementById('all-in-button');
    const foldButton = document.getElementById('fold-button');
    const restartButton = document.getElementById('restart-button');

    const communityCardsArea = document.getElementById('community-cards-area');
    const playerAreasContainer = document.getElementById('player-areas');
    const potSizeSpan = document.getElementById('pot-size');
    const logMessagesUl = document.getElementById('log-messages');
    const handsPlayedSpan = document.getElementById('hands-played');
    const winnerDisplay = document.getElementById('winner-display');
    
    const userCard1Span = document.getElementById('user-card1');
    const userCard2Span = document.getElementById('user-card2');
    const userPositionSpan = document.getElementById('user-position');

    // For performance graph (using Chart.js or similar)
    let performanceChart = null; 
    const chartCanvas = document.getElementById('performanceChart');

    const CARD_IMAGE_PATH = '/static/card_images/';

    const hamburgerIcon = document.getElementById('hamburger-menu-icon');
    const sideMenu = document.getElementById('side-menu');
    const menuLinks = document.querySelectorAll('#side-menu .menu-link');
    const pageViews = document.querySelectorAll('.page-view');
    const mainContentArea = document.getElementById('main-content-area'); // If needed for specific manipulations

    if (hamburgerIcon && sideMenu) {
        hamburgerIcon.addEventListener('click', () => {
            hamburgerIcon.classList.toggle('open');
            sideMenu.classList.toggle('open');
        });
    }

    menuLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const targetPageId = link.getAttribute('data-page');

            pageViews.forEach(page => {
                if (page.id === targetPageId) {
                    page.classList.add('active-page');
                    // page.style.display = 'block'; // Alternative to class-based display
                } else {
                    page.classList.remove('active-page');
                    // page.style.display = 'none'; // Alternative
                }
            });

            // Close the menu
            if (hamburgerIcon && sideMenu) {
                hamburgerIcon.classList.remove('open');
                sideMenu.classList.remove('open');
            }
        });
    });

    async function fetchAndUpdateState() {
        try {
            const response = await fetch('/get_state');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const state = await response.json();
            updateUI(state);
        } catch (error) {
            console.error("Error fetching state:", error);
            logMessagesUl.innerHTML += `<li>Error fetching state: ${error.message}</li>`;
        }
    }

    function updateUI(state) {
        // Log messages
        logMessagesUl.innerHTML = ''; // Clear old logs
        state.log_messages.forEach(msg => {
            const li = document.createElement('li');
            li.textContent = msg;
            logMessagesUl.appendChild(li);
        });
        logMessagesUl.scrollTop = logMessagesUl.scrollHeight; // Scroll to bottom

        // Hands played
        handsPlayedSpan.textContent = state.hands_played;

        // Pot size
        potSizeSpan.textContent = state.pot_size.toFixed(2);

        // Clear previous winner highlights and current player highlight before rebuilding
        document.querySelectorAll('.player-area.winner-player').forEach(el => el.classList.remove('winner-player'));
        document.querySelectorAll('.player-area.current-player').forEach(el => el.classList.remove('current-player'));

        playerAreasContainer.innerHTML = ''; // Clear old player areas
        state.players.forEach((playerName, index) => {
            const playerArea = document.createElement('div');
            playerArea.classList.add('player-area');
            playerArea.id = `player-${playerName}`; // e.g. player-CO

            if (index === state.user_player_position_idx && state.game_phase === "awaiting_decision") {
                 playerArea.classList.add('current-player');
            }
            // else { // Not strictly necessary to remove if clearing all and rebuilding
            //      playerArea.classList.remove('current-player');
            // }

            // Highlight winner(s) at showdown
            if (state.game_phase === "showdown" && state.winner_indices && state.winner_indices.includes(index)) {
                playerArea.classList.add('winner-player');
            }

            const nameDiv = document.createElement('div');
            nameDiv.classList.add('player-name');
            nameDiv.textContent = `${playerName} (${state.player_stacks[index].toFixed(2)} BB)`;
            playerArea.appendChild(nameDiv);

            const cardsDiv = document.createElement('div');
            cardsDiv.classList.add('player-cards');
            
            // Use state.all_player_cards_display which is prepared by backend
            const playerCardsToDisplay = (state.all_player_cards_display && state.all_player_cards_display[index]) 
                                       ? state.all_player_cards_display[index] 
                                       : ['back.png', 'back.png'];

            playerCardsToDisplay.forEach(cardFile => {
                const cardImg = document.createElement('img');
                cardImg.src = CARD_IMAGE_PATH + cardFile;
                cardImg.alt = cardFile.split('.')[0]; 
                cardsDiv.appendChild(cardImg);
            });
            playerArea.appendChild(cardsDiv);

            // Always show decisions if they exist
            if (state.decisions && state.decisions[index]) {
                const decisionDiv = document.createElement('div');
                decisionDiv.classList.add('player-decision');
                decisionDiv.textContent = state.decisions[index];
                if (state.decisions[index] === "FOLD") decisionDiv.classList.add("fold");
                if (state.decisions[index] === "ALL_IN") decisionDiv.classList.add("all-in");
                // Add other decision styles if needed
                playerArea.appendChild(decisionDiv);
            }
            playerAreasContainer.appendChild(playerArea);
        });
        
        // User's hand display (separate for clarity) - uses state.user_hand_display from backend
        if (state.user_hand_display && state.user_hand_display.length === 2 && state.user_hand_display[0] !== '?') {
            userCard1Span.textContent = state.user_hand_display[0];
            userCard2Span.textContent = state.user_hand_display[1];
        } else {
            userCard1Span.textContent = '?';
            userCard2Span.textContent = '?';
        }
        userPositionSpan.textContent = state.players[state.user_player_position_idx]; // Shows current/next position

        // Community cards (lines 106-122)
        // This logic should be fine as state.community_cards_display is now set by backend for showdown
        communityCardsArea.innerHTML = '';
        (state.community_cards_display || []).forEach(cardFile => {
            if (cardFile) { 
                const cardImg = document.createElement('img');
                cardImg.src = CARD_IMAGE_PATH + cardFile;
                cardImg.alt = cardFile.split('.')[0];
                communityCardsArea.appendChild(cardImg);
            }
        });
        // If fewer than 5 community cards are sent (e.g. not showdown), fill with backs
        const revealedCount = (state.community_cards_display || []).length;
        if (state.game_phase !== "showdown" || revealedCount < 5) { // Show 5 backs if not showdown or not all revealed
            for (let i = revealedCount; i < 5; i++) {
                const cardImg = document.createElement('img');
                cardImg.src = CARD_IMAGE_PATH + 'back.png';
                cardImg.alt = 'Card Back';
                communityCardsArea.appendChild(cardImg);
            }
        }

        // Winner display text (lines 126-130)
        if (state.game_phase === "showdown" && state.winner_info) { // Check phase for winner display
            winnerDisplay.textContent = `Winner: ${state.winner_info.name} with ${state.winner_info.hand_type}`;
        } else {
            winnerDisplay.textContent = ''; // Clear if not showdown or no winner
        }

        // Button states
        if (state.game_phase === "awaiting_decision") {
            dealButton.disabled = true;
            allInButton.disabled = false;
            foldButton.disabled = false;
        } else { // "pre_deal" or "showdown"
            dealButton.disabled = false;
            allInButton.disabled = true;
            foldButton.disabled = true;
        }
        
        // Performance Graph Update
        if (state.player_cumulative_bb && typeof Chart !== 'undefined') { // Check if Chart.js is loaded
            const labels = Array.from({ length: state.player_cumulative_bb.length }, (_, i) => i);
            const data = {
                labels: labels,
                datasets: [{
                    label: 'Cumulative BB Won/Lost',
                    backgroundColor: 'rgb(75, 192, 192)',
                    borderColor: 'rgb(75, 192, 192)',
                    data: state.player_cumulative_bb,
                    fill: false,
                    tension: 0.1
                }]
            };
            if (performanceChart) {
                performanceChart.data = data;
                performanceChart.update('none');
            } else {
                performanceChart = new Chart(chartCanvas, {
                    type: 'line',
                    data: data,
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: false // Allow negative values for losses
                            }
                        }
                    }
                });
            }
        }
    }

    dealButton.addEventListener('click', async () => {
        await fetch('/deal', { method: 'POST' });
        fetchAndUpdateState();
    });

    allInButton.addEventListener('click', async () => {
        await fetch('/make_decision/ALL_IN', { method: 'POST' });
        fetchAndUpdateState();
    });

    foldButton.addEventListener('click', async () => {
        await fetch('/make_decision/FOLD', { method: 'POST' });
        fetchAndUpdateState();
    });

    restartButton.addEventListener('click', async () => {
        await fetch('/restart', { method: 'POST' });
        fetchAndUpdateState(); // Fetch initial state after restart
    });

    // Initial state load
    fetchAndUpdateState();
}); 