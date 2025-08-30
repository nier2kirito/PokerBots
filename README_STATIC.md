# Static All-In or Fold Poker Game

This is a static version of the All-In or Fold poker game that can be hosted for free on any static hosting platform.

## Files Structure

```
/
├── index.html                     # Main game file (standalone)
├── static/
│   ├── aggregated_results.json   # Strategy data (converted from pickle)
│   ├── card_images/              # Card images (PNG files)
│   │   ├── Ac.png, Ad.png, etc. # All 52 card images + back.png
│   ├── style.css                 # Game styling
│   └── styles.css                # Additional styles
```

## How to Host

### Option 1: GitHub Pages
1. Create a new GitHub repository
2. Upload all files maintaining the folder structure
3. Enable GitHub Pages in repository settings
4. Your game will be available at `https://yourusername.github.io/repository-name`

### Option 2: Netlify
1. Create account at netlify.com
2. Drag and drop the entire folder to Netlify
3. Your game will be automatically deployed

### Option 3: Vercel
1. Create account at vercel.com
2. Connect your GitHub repository or upload files
3. Deploy with one click

### Option 4: Local Testing
```bash
# Navigate to the game directory
cd /path/to/game

# Start a simple HTTP server
python3 -m http.server 8000

# Open http://localhost:8000 in your browser
```

## What Was Converted

- **Flask Backend → JavaScript**: All game logic now runs in the browser
- **Pickle File → JSON**: Strategy data converted to `aggregated_results.json`
- **Server Routes → Client Functions**: Deal, decision-making, and game state management
- **Session Storage → Local Variables**: Game state maintained in browser memory
- **Card Images**: Already static, just needed path updates

## Features Preserved

- ✅ All-In or Fold gameplay
- ✅ 4-player poker (CO, BTN, SB, BB)
- ✅ Optimal bot strategy using converted data
- ✅ Hand evaluation and winner determination
- ✅ Performance tracking with Chart.js
- ✅ Responsive design
- ✅ Card animations and UI

## Browser Compatibility

- Chrome, Firefox, Edge (recommended)
- Safari (should work)
- Mobile browsers (responsive design)

## File Sizes

- `index.html`: ~50KB (includes all JavaScript)
- `aggregated_results.json`: ~200KB (strategy data)
- Card images: ~2.5MB total (53 PNG files)
- CSS files: ~20KB total

Total: ~2.8MB - perfect for free hosting platforms!

## Notes

- No server required - runs entirely in the browser
- Strategy data loads asynchronously
- Game state resets on page refresh (no persistence)
- All original Flask functionality preserved
