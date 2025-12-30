/**
 * Banana-Bench Game Visualizer
 * Interactive playback of Bananagrams game results
 */

// ============================================
// State Management
// ============================================

const state = {
  gameData: null,
  currentTurn: 0,
  isPlaying: false,
  playbackSpeed: 1,
  playInterval: null,
  playerStations: {},
  previousGrids: {},  // Track grids per player to only animate changes
  typewriterInterval: null,
  isAnimating: false,  // Prevent rapid navigation during animations
};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  // Load embedded game data
  const dataScript = document.getElementById('game-data');
  state.gameData = JSON.parse(dataScript.textContent);

  // Initialize the visualizer
  initializeTable();
  initializeTimeline();
  initializeControls();
  initializeNotification();

  // Show initial state (turn 0)
  renderTurn(0);
});

function initializeTable() {
  const table = document.getElementById('game-table');
  const players = state.gameData.config.players;

  // Create player stations side by side
  players.forEach((playerConfig, index) => {
    const playerId = `p${index + 1}`;
    const station = createPlayerStation(playerId, playerConfig);
    state.playerStations[playerId] = station;
    table.appendChild(station);
  });
}

function createPlayerStation(playerId, config) {
  const station = document.createElement('div');
  station.className = 'player-station';
  station.setAttribute('data-player', playerId);

  station.innerHTML = `
    <div class="player-info">
      <div>
        <div class="player-name">${config.name || config.model}</div>
        <div class="player-model">${config.model}</div>
      </div>
      <div class="player-status">
        <span class="status-icon"></span>
      </div>
    </div>

    <div class="thinking-panel">
      <div class="thinking-header">
        <span class="thinking-icon">💭</span>
        <span class="thinking-label">Thinking</span>
      </div>
      <div class="thinking-text empty">Waiting for turn...</div>
    </div>

    <div class="player-right-column">
      <div class="player-board">
        <span class="board-empty">No board yet</span>
      </div>

      <div class="player-hand"></div>
    </div>

    <div class="validation-bar pending">
      <span class="validation-icon">⏳</span>
      <div class="validation-content">
        <div class="validation-status">Waiting...</div>
      </div>
    </div>
  `;

  return station;
}

function initializeTimeline() {
  const track = document.getElementById('timeline-track');
  const turns = state.gameData.turn_history;

  // Calculate adaptive marker width based on turn count
  // Aim to fit all markers in the available space
  const padding = 12; // 6px on each side
  const trackWidth = track.offsetWidth - padding;
  const gap = 1; // Gap between markers
  const totalGaps = (turns.length - 1) * gap;
  const availableWidth = trackWidth - totalGaps;
  const calculatedWidth = availableWidth / turns.length;

  // Constrain between min (2px) and max (12px) for usability
  const markerWidth = Math.max(2, Math.min(12, calculatedWidth));

  // Apply the calculated width to all markers via CSS variable
  track.style.setProperty('--marker-width', `${markerWidth}px`);

  // Create markers for each turn
  turns.forEach((turn, index) => {
    const marker = document.createElement('div');
    marker.className = 'timeline-marker';
    marker.setAttribute('data-turn', index);
    marker.setAttribute('data-player', turn.player_id);

    // Color based on turn outcome (priority order matters)
    if (turn.auto_bananas) {
      marker.classList.add('win');
    } else if (turn.auto_peeled) {
      marker.classList.add('peel');
    } else if (turn.action === 'DUMP') {
      marker.classList.add('dump');
    } else if (turn.validation && turn.validation.valid) {
      marker.classList.add('valid');
    } else {
      marker.classList.add('invalid');
    }

    marker.addEventListener('click', () => {
      if (!state.isAnimating) goToTurn(index);
    });
    track.insertBefore(marker, document.getElementById('timeline-handle'));
  });

  // Setup scrubber drag
  setupTimelineDrag();

  // Update total turns display
  document.getElementById('total-turns').textContent = turns.length;
}

function initializeNotification() {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = 'action-notification';
  notification.id = 'action-notification';
  document.body.appendChild(notification);
}

function setupTimelineDrag() {
  const track = document.getElementById('timeline-track');
  const handle = document.getElementById('timeline-handle');
  let isDragging = false;

  const updateFromPosition = (e) => {
    if (state.isAnimating) return;

    // Get the actual marker area bounds
    const markers = track.querySelectorAll('.timeline-marker');
    if (markers.length === 0) return;

    const firstMarker = markers[0];
    const lastMarker = markers[markers.length - 1];

    const markerAreaStart = firstMarker.offsetLeft + (firstMarker.offsetWidth / 2);
    const markerAreaEnd = lastMarker.offsetLeft + (lastMarker.offsetWidth / 2);
    const markerAreaWidth = markerAreaEnd - markerAreaStart;

    // Calculate position relative to the marker area
    const rect = track.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const relativeX = Math.max(0, Math.min(clickX - markerAreaStart, markerAreaWidth));
    const percent = relativeX / markerAreaWidth;

    const turnIndex = Math.round(percent * (state.gameData.turn_history.length - 1));
    goToTurn(turnIndex, false);  // Skip animation when scrubbing
  };

  track.addEventListener('mousedown', (e) => {
    if (e.target !== handle && !state.isAnimating) {
      updateFromPosition(e);
    }
    isDragging = true;
  });

  document.addEventListener('mousemove', (e) => {
    if (isDragging) {
      updateFromPosition(e);
    }
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
  });
}

function initializeControls() {
  document.getElementById('btn-prev').addEventListener('click', () => {
    if (!state.isAnimating) stepTurn(-1, false);
  });
  document.getElementById('btn-play').addEventListener('click', togglePlay);
  document.getElementById('btn-next').addEventListener('click', () => {
    if (!state.isAnimating) stepTurn(1, false);
  });

  document.getElementById('speed-select').addEventListener('change', (e) => {
    state.playbackSpeed = parseFloat(e.target.value);
    if (state.isPlaying) {
      stopPlayback();
      startPlayback();
    }
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (state.isAnimating && e.code !== 'Escape') return;

    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.code === 'ArrowLeft') {
      stepTurn(-1, false);
    } else if (e.code === 'ArrowRight') {
      stepTurn(1, false);
    } else if (e.code === 'Escape') {
      stopPlayback();
      cancelAnimations();
    }
  });
}

// ============================================
// Playback Control
// ============================================

function togglePlay() {
  if (state.isPlaying) {
    stopPlayback();
  } else {
    startPlayback();
  }
}

function startPlayback() {
  state.isPlaying = true;
  document.getElementById('btn-play').textContent = '⏸';
  document.getElementById('btn-play').classList.add('playing');

  advanceWithAnimation();
}

function advanceWithAnimation() {
  if (!state.isPlaying) return;

  if (state.currentTurn < state.gameData.turn_history.length - 1) {
    stepTurn(1, true);
  } else {
    stopPlayback();
  }
}

function stopPlayback() {
  state.isPlaying = false;
  document.getElementById('btn-play').textContent = '▶';
  document.getElementById('btn-play').classList.remove('playing');

  if (state.playInterval) {
    clearTimeout(state.playInterval);
    state.playInterval = null;
  }
}

function cancelAnimations() {
  state.isAnimating = false;
  if (state.typewriterInterval) {
    clearInterval(state.typewriterInterval);
    state.typewriterInterval = null;
  }
}

function stepTurn(delta, animate = true) {
  const newTurn = Math.max(0, Math.min(
    state.currentTurn + delta,
    state.gameData.turn_history.length - 1
  ));

  if (newTurn !== state.currentTurn) {
    goToTurn(newTurn, animate);
  }
}

function goToTurn(turnIndex, animate = true) {
  cancelAnimations();
  state.currentTurn = turnIndex;
  renderTurn(turnIndex, animate);
  updateTimelineHandle();
}

// ============================================
// Rendering with Phased Animation
// ============================================

function renderTurn(turnIndex, animate = true) {
  const turn = state.gameData.turn_history[turnIndex];
  if (!turn) return;

  const activePlayerId = turn.player_id;

  // Update all player stations
  Object.keys(state.playerStations).forEach((playerId) => {
    const station = state.playerStations[playerId];
    const isActive = playerId === activePlayerId;

    station.classList.toggle('active', isActive);

    // Find the latest turn for this player up to current turn
    const playerTurn = findLatestPlayerTurn(playerId, turnIndex);

    if (isActive && animate) {
      // Active player: animate with phases
      renderActivePlayerWithAnimation(playerId, turn);
    } else if (isActive && !animate) {
      // Active player without animation (e.g., scrubbing timeline)
      renderPlayerStatic(playerId, turn);
    } else if (playerTurn) {
      // Inactive player: just show their last state (no animation)
      renderPlayerStatic(playerId, playerTurn);
    } else {
      renderInitialState(playerId);
    }

    // Scroll to active player
    if (isActive) {
      scrollToPlayer(playerId);
    }
  });

  // Update bunch count
  updateBunchCount(turnIndex);

  // Update turn info
  updateTurnInfo(turn, turnIndex);

  // PEEL flash and notification will be shown after animation completes
  // (moved to renderActivePlayerWithAnimation)
}

function renderActivePlayerWithAnimation(playerId, turn) {
  const station = state.playerStations[playerId];
  state.isAnimating = true;

  // Set validation bar to pending initially
  const validationBar = station.querySelector('.validation-bar');
  validationBar.className = 'validation-bar pending';
  validationBar.querySelector('.validation-icon').textContent = '⏳';
  validationBar.querySelector('.validation-content').innerHTML = '<div class="validation-status">Processing...</div>';

  // Phase 1: Clear thinking and show "thinking..."
  const thinkingText = station.querySelector('.thinking-text');
  thinkingText.innerHTML = '';
  thinkingText.classList.remove('empty');

  // Phase 2: Stream the thinking text with typewriter effect
  const thinkingContent = turn.thinking || 'No strategy shared...';
  let charIndex = 0;

  // Calculate speed based on text length and playback speed
  const baseCharsPerSecond = 100;
  const charsPerInterval = Math.max(1, Math.floor(state.playbackSpeed * 3));
  const intervalMs = 1000 / baseCharsPerSecond;

  state.typewriterInterval = setInterval(() => {
    if (charIndex < thinkingContent.length) {
      thinkingText.textContent = thinkingContent.substring(0, charIndex + charsPerInterval);
      charIndex += charsPerInterval;
      // Auto-scroll
      thinkingText.parentElement.scrollTop = thinkingText.parentElement.scrollHeight;
    } else {
      clearInterval(state.typewriterInterval);
      state.typewriterInterval = null;

      // Phase 3: After thinking complete, show board
      setTimeout(() => {
        renderPlayerBoard(playerId, turn, true);
        renderPlayerHand(playerId, turn);
        updatePlayerStatus(playerId, turn);

        // Phase 4: After board renders, show validation with delay
        setTimeout(() => {
          renderValidation(playerId, turn);

          // Phase 5: After validation, show notification (PEEL/DUMP/BANANAS)
          setTimeout(() => {
            showActionNotification(turn);

            // PEEL flash on bunch
            if (turn.auto_peeled) {
              document.getElementById('bunch-pile').classList.add('peel-flash');
              setTimeout(() => {
                document.getElementById('bunch-pile').classList.remove('peel-flash');
              }, 600);
            }

            state.isAnimating = false;

            // If playing, schedule next turn
            if (state.isPlaying) {
              const delay = 1500 / state.playbackSpeed;
              state.playInterval = setTimeout(() => advanceWithAnimation(), delay);
            }
          }, 200 / state.playbackSpeed);
        }, 400 / state.playbackSpeed);
      }, 300 / state.playbackSpeed);
    }
  }, intervalMs / state.playbackSpeed);
}

function renderPlayerStatic(playerId, turn) {
  const station = state.playerStations[playerId];

  // Show thinking (full, no animation)
  const thinkingText = station.querySelector('.thinking-text');
  if (turn.thinking) {
    thinkingText.textContent = turn.thinking;
    thinkingText.classList.remove('empty');
  } else {
    thinkingText.textContent = 'No strategy shared...';
    thinkingText.classList.add('empty');
  }

  // Show board without animation
  renderPlayerBoard(playerId, turn, false);
  renderValidation(playerId, turn);
  renderPlayerHand(playerId, turn);
  updatePlayerStatus(playerId, turn);
}

function renderPlayerBoard(playerId, turn, animate) {
  const station = state.playerStations[playerId];
  const boardContainer = station.querySelector('.player-board');

  if (turn.validation && turn.validation.grid) {
    const prevGrid = animate ? state.previousGrids[playerId] : null;
    boardContainer.innerHTML = '';
    boardContainer.appendChild(renderBoard(turn.validation.grid, prevGrid, animate, boardContainer));
    state.previousGrids[playerId] = turn.validation.grid;
  } else {
    boardContainer.innerHTML = '<span class="board-empty">No valid board</span>';
  }
}

function renderValidation(playerId, turn) {
  const station = state.playerStations[playerId];
  const validationBar = station.querySelector('.validation-bar');
  const icon = validationBar.querySelector('.validation-icon');
  const content = validationBar.querySelector('.validation-content');

  const errors = turn.validation?.errors || [];
  const isValid = turn.validation?.valid || false;

  // Remove all state classes
  validationBar.className = 'validation-bar';

  if (isValid) {
    // Valid board - green bar
    validationBar.classList.add('valid');
    icon.textContent = '✓';
    content.innerHTML = '<div class="validation-status">Valid Board</div>';
  } else if (errors.length > 0) {
    // Invalid board - red bar with errors
    validationBar.classList.add('invalid');
    icon.textContent = '⚠️';

    // Group errors by type for better display
    const errorsByType = {};
    errors.forEach(err => {
      const type = err.code || 'ERROR';
      if (!errorsByType[type]) errorsByType[type] = [];
      errorsByType[type].push(err);
    });

    // Build error list
    let errorHtml = '<div class="validation-errors">';
    let displayCount = 0;

    for (const [type, errs] of Object.entries(errorsByType)) {
      if (displayCount >= 5) break;

      errs.slice(0, 5 - displayCount).forEach(err => {
        // Format based on error type
        if (err.code === 'LETTER_MISMATCH' && err.word) {
          errorHtml += `<div class="validation-error"><strong>${err.word}</strong>: Letter mismatch at connection point</div>`;
        } else if (err.code === 'GRID_CONFLICT' && err.word) {
          errorHtml += `<div class="validation-error"><strong>${err.word}</strong>: Overlaps with existing tile</div>`;
        } else if (err.code === 'INVALID_WORD' && err.word) {
          errorHtml += `<div class="validation-error"><strong>${err.word}</strong>: Not in dictionary</div>`;
        } else if (err.code === 'ACCIDENTAL_INVALID' && err.word) {
          errorHtml += `<div class="validation-error"><strong>${err.word}</strong>: Accidental word not valid</div>`;
        } else if (err.code === 'TILES_NOT_IN_HAND') {
          errorHtml += `<div class="validation-error">Using tiles not in hand</div>`;
        } else {
          errorHtml += `<div class="validation-error">${truncateText(err.message, 70)}</div>`;
        }
        displayCount++;
      });
    }

    if (errors.length > 5) {
      errorHtml += `<div class="validation-error" style="font-style: italic; opacity: 0.7;">...and ${errors.length - 5} more errors</div>`;
    }

    errorHtml += '</div>';
    content.innerHTML = errorHtml;
  } else {
    // Pending/waiting state
    validationBar.classList.add('pending');
    icon.textContent = '⏳';
    content.innerHTML = '<div class="validation-status">Waiting...</div>';
  }
}

function renderPlayerHand(playerId, turn) {
  const station = state.playerStations[playerId];
  const handContainer = station.querySelector('.player-hand');
  handContainer.innerHTML = '';

  const tilesBefore = turn.tiles_before || [];
  const tilesAfter = turn.tiles_after || [];
  const grid = turn.validation?.grid || '';

  // Parse tiles on the board from the grid
  const tilesOnBoard = [];
  for (let char of grid) {
    if (char.match(/[A-Z]/)) {
      tilesOnBoard.push(char);
    }
  }

  // Count tiles in hand and on board
  const handCounter = {};
  const boardCounter = {};

  tilesBefore.forEach(tile => {
    handCounter[tile] = (handCounter[tile] || 0) + 1;
  });

  tilesOnBoard.forEach(tile => {
    boardCounter[tile] = (boardCounter[tile] || 0) + 1;
  });

  // Build lists of used vs unused tiles from the hand
  const tilesUsedOnBoard = [];
  const tilesUnused = [];

  const handCounterCopy = {...handCounter};

  // First, extract tiles that are on the board
  for (let tile in boardCounter) {
    const countOnBoard = boardCounter[tile];
    const countInHand = handCounterCopy[tile] || 0;
    const usedFromHand = Math.min(countOnBoard, countInHand);

    for (let i = 0; i < usedFromHand; i++) {
      tilesUsedOnBoard.push(tile);
      handCounterCopy[tile]--;
    }
  }

  // Remaining tiles in hand are unused
  for (let tile in handCounterCopy) {
    for (let i = 0; i < handCounterCopy[tile]; i++) {
      tilesUnused.push(tile);
    }
  }

  // Detect new tiles (in tilesAfter but not in tilesBefore)
  const beforeCounter = {};
  const afterCounter = {};

  tilesBefore.forEach(tile => {
    beforeCounter[tile] = (beforeCounter[tile] || 0) + 1;
  });

  tilesAfter.forEach(tile => {
    afterCounter[tile] = (afterCounter[tile] || 0) + 1;
  });

  const newTiles = [];
  for (let tile in afterCounter) {
    const newCount = afterCounter[tile] - (beforeCounter[tile] || 0);
    for (let i = 0; i < newCount; i++) {
      newTiles.push(tile);
    }
  }

  // Render tiles used on board (if any)
  if (tilesUsedOnBoard.length > 0) {
    const usedLabel = document.createElement('div');
    usedLabel.className = 'hand-section-label';
    usedLabel.textContent = 'On Board:';
    handContainer.appendChild(usedLabel);

    tilesUsedOnBoard.sort().forEach((letter) => {
      const tile = document.createElement('div');
      tile.className = 'hand-tile used';
      tile.textContent = letter;
      handContainer.appendChild(tile);
    });
  }

  // Render unused tiles
  if (tilesUnused.length > 0) {
    if (tilesUsedOnBoard.length > 0) {
      const divider = document.createElement('div');
      divider.className = 'hand-divider';
      handContainer.appendChild(divider);
    }

    const unusedLabel = document.createElement('div');
    unusedLabel.className = 'hand-section-label';
    unusedLabel.textContent = 'Unused:';
    handContainer.appendChild(unusedLabel);

    tilesUnused.sort().forEach((letter) => {
      const tile = document.createElement('div');
      tile.className = 'hand-tile';
      tile.textContent = letter;
      handContainer.appendChild(tile);
    });
  }

  // Render new tiles (if any)
  if (newTiles.length > 0) {
    if (tilesUsedOnBoard.length > 0 || tilesUnused.length > 0) {
      const divider = document.createElement('div');
      divider.className = 'hand-divider';
      handContainer.appendChild(divider);
    }

    const newLabel = document.createElement('div');
    newLabel.className = 'hand-section-label';
    newLabel.textContent = 'New:';
    handContainer.appendChild(newLabel);

    newTiles.sort().forEach((letter) => {
      const tile = document.createElement('div');
      tile.className = 'hand-tile new';
      tile.textContent = letter;
      handContainer.appendChild(tile);
    });
  }
}

function updatePlayerStatus(playerId, turn) {
  const station = state.playerStations[playerId];
  const statusIcon = station.querySelector('.status-icon');

  if (turn.auto_bananas) {
    statusIcon.textContent = '🏆';
    statusIcon.className = 'status-icon status-winner';
    station.classList.add('winner');
  } else if (turn.validation && turn.validation.valid) {
    statusIcon.textContent = '✓';
    statusIcon.className = 'status-icon status-valid';
  } else {
    statusIcon.textContent = '✗';
    statusIcon.className = 'status-icon status-invalid';
  }
}

function renderInitialState(playerId) {
  const station = state.playerStations[playerId];

  // Thinking
  const thinkingText = station.querySelector('.thinking-text');
  thinkingText.textContent = 'Waiting for turn...';
  thinkingText.classList.add('empty');

  // Validation bar to pending
  const validationBar = station.querySelector('.validation-bar');
  validationBar.className = 'validation-bar pending';
  validationBar.querySelector('.validation-icon').textContent = '⏳';
  validationBar.querySelector('.validation-content').innerHTML = '<div class="validation-status">Waiting...</div>';

  // Board empty
  station.querySelector('.player-board').innerHTML = '<span class="board-empty">No board yet</span>';

  // Hand empty
  station.querySelector('.player-hand').innerHTML = '';

  // Status
  const statusIcon = station.querySelector('.status-icon');
  statusIcon.textContent = '';
  statusIcon.className = 'status-icon';
}

function findLatestPlayerTurn(playerId, upToIndex) {
  for (let i = upToIndex; i >= 0; i--) {
    const turn = state.gameData.turn_history[i];
    if (turn.player_id === playerId) {
      return turn;
    }
  }
  return null;
}

// ============================================
// Board Rendering
// ============================================

function renderBoard(asciiGrid, prevGrid, animate, boardContainer) {
  const container = document.createElement('div');
  container.className = 'board-grid';

  const rows = asciiGrid.split('\n');
  const height = rows.length;
  const width = Math.max(...rows.map(r => r.length));

  const tileSize = computeBoardTileSize(boardContainer, width, height);
  const fontSize = Math.max(10, Math.floor(tileSize * 0.6));

  container.style.setProperty('--board-tile-size', `${tileSize}px`);
  container.style.setProperty('--board-font-size', `${fontSize}px`);
  container.style.gridTemplateColumns = `repeat(${width}, ${tileSize}px)`;
  container.style.gridTemplateRows = `repeat(${height}, ${tileSize}px)`;

  // Parse previous grid for comparison (only if animating)
  const prevTiles = (animate && prevGrid) ? parseTiles(prevGrid) : new Set();

  rows.forEach((row, y) => {
    for (let x = 0; x < width; x++) {
      const char = row[x] || '.';
      const key = `${x},${y},${char}`;

      if (char !== '.') {
        const tile = document.createElement('div');
        tile.className = 'tile';
        tile.textContent = char;

        if (animate) {
          tile.classList.add('animate');
          tile.style.animationDelay = `${(x + y) * 0.03}s`;

          // Check if this is a new tile
          if (!prevTiles.has(key)) {
            tile.classList.add('new');
          }
        }

        container.appendChild(tile);
      } else {
        const empty = document.createElement('div');
        empty.className = 'tile-empty';
        container.appendChild(empty);
      }
    }
  });

  return container;
}

function computeBoardTileSize(boardContainer, gridWidth, gridHeight) {
  const maxSize = 24;
  const minSize = 12;
  const gap = 2;

  if (!boardContainer) {
    return maxSize;
  }

  const styles = getComputedStyle(boardContainer);
  const paddingX = parseFloat(styles.paddingLeft) + parseFloat(styles.paddingRight);
  const paddingY = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
  const availableWidth = Math.max(0, boardContainer.clientWidth - paddingX);
  const availableHeight = Math.max(0, boardContainer.clientHeight - paddingY);

  if (!availableWidth || !availableHeight) {
    return maxSize;
  }

  const tileFromWidth = Math.floor((availableWidth - gap * (gridWidth - 1)) / gridWidth);
  const tileFromHeight = Math.floor((availableHeight - gap * (gridHeight - 1)) / gridHeight);
  const tileSize = Math.min(maxSize, tileFromWidth, tileFromHeight);

  return Math.max(minSize, tileSize);
}

function parseTiles(asciiGrid) {
  const tiles = new Set();
  const rows = asciiGrid.split('\n');
  rows.forEach((row, y) => {
    [...row].forEach((char, x) => {
      if (char !== '.') {
        tiles.add(`${x},${y},${char}`);
      }
    });
  });
  return tiles;
}

// ============================================
// UI Updates
// ============================================

function updateBunchCount(turnIndex) {
  // Calculate bunch count at this turn
  const initialBunch = 144;
  const numPlayers = state.gameData.config.players.length;
  const startingHand = numPlayers <= 4 ? 21 : (numPlayers <= 6 ? 15 : 11);
  let bunchCount = initialBunch - (startingHand * numPlayers);

  // Count PEEL and DUMP actions up to this turn
  for (let i = 0; i <= turnIndex; i++) {
    const turn = state.gameData.turn_history[i];
    if (turn.auto_peeled) {
      bunchCount -= numPlayers;
    }
    if (turn.action === 'DUMP') {
      bunchCount -= 2;
    }
  }

  bunchCount = Math.max(0, bunchCount);
  document.getElementById('bunch-count-number').textContent = bunchCount;
}

function updateTurnInfo(turn, turnIndex) {
  document.getElementById('current-turn').textContent = turnIndex + 1;

  // Player info
  const playerConfig = state.gameData.config.players[parseInt(turn.player_id.substring(1)) - 1];
  document.getElementById('turn-player').textContent = playerConfig.name || playerConfig.model;

  // Status
  const statusEl = document.getElementById('turn-status');
  statusEl.className = 'turn-status';

  if (turn.auto_bananas) {
    statusEl.textContent = '🏆 BANANAS!';
    statusEl.classList.add('win');
  } else if (turn.auto_peeled) {
    statusEl.textContent = '🍌 PEEL!';
    statusEl.classList.add('peel');
  } else if (turn.validation && turn.validation.valid) {
    statusEl.textContent = '✓ Valid';
    statusEl.classList.add('valid');
  } else {
    const errorCount = turn.validation?.errors?.length || 0;
    statusEl.textContent = `✗ ${errorCount} error${errorCount !== 1 ? 's' : ''}`;
    statusEl.classList.add('invalid');
  }
}

function updateTimelineHandle() {
  const handle = document.getElementById('timeline-handle');
  const track = document.getElementById('timeline-track');
  const totalTurns = state.gameData.turn_history.length;

  if (totalTurns === 0) return;

  const percent = totalTurns > 1
    ? state.currentTurn / (totalTurns - 1)
    : 0;

  // Get the actual marker positions to align the handle correctly
  const markers = track.querySelectorAll('.timeline-marker');
  if (markers.length === 0) return;

  const firstMarker = markers[0];
  const lastMarker = markers[markers.length - 1];

  // Calculate the actual start and end of the marker area
  const markerAreaStart = firstMarker.offsetLeft + (firstMarker.offsetWidth / 2);
  const markerAreaEnd = lastMarker.offsetLeft + (lastMarker.offsetWidth / 2);
  const markerAreaWidth = markerAreaEnd - markerAreaStart;

  // Position handle within the actual marker area
  const position = markerAreaStart + (markerAreaWidth * percent);
  handle.style.left = `${position}px`;
}

// ============================================
// Action Notifications
// ============================================

function showActionNotification(turn) {
  const notification = document.getElementById('action-notification');
  if (!notification) return;

  let message = '';
  let type = '';

  // Get player name
  const playerIndex = parseInt(turn.player_id.substring(1)) - 1;
  const playerConfig = state.gameData.config.players[playerIndex];
  const playerName = playerConfig.name || playerConfig.model;

  // Determine notification type and message
  if (turn.auto_bananas) {
    type = 'bananas';
    message = `<span class="notification-icon">🏆</span> <span class="player-name-notification">${playerName}</span> BANANAS!`;
  } else if (turn.auto_peeled) {
    type = 'peel';
    message = `<span class="notification-icon">🍌</span> <span class="player-name-notification">${playerName}</span> PEEL!`;
  } else if (turn.action === 'DUMP') {
    type = 'dump';
    const dumpedTile = turn.dump_tile || '?';
    message = `<span class="notification-icon">🗑️</span> <span class="player-name-notification">${playerName}</span> DUMP <span class="dump-tile">${dumpedTile}</span>`;
  }

  // Only show if there's a message
  if (message) {
    // Remove existing classes
    notification.className = 'action-notification';

    // Set new content and type
    notification.innerHTML = message;
    notification.classList.add(type);
    notification.setAttribute('data-player', turn.player_id);

    // Trigger animation
    setTimeout(() => {
      notification.classList.add('visible');
    }, 10);

    // Remove after animation completes
    setTimeout(() => {
      notification.classList.remove('visible');
    }, 2400 / state.playbackSpeed);
  }
}

// ============================================
// Utilities
// ============================================

function scrollToPlayer(playerId) {
  const station = state.playerStations[playerId];
  if (!station) return;

  const gameTable = document.getElementById('game-table');
  if (!gameTable) return;

  // Calculate the scroll position to center the player
  const stationRect = station.getBoundingClientRect();
  const tableRect = gameTable.getBoundingClientRect();

  // Calculate offset to center the station in the viewport
  const scrollOffset = station.offsetLeft - (tableRect.width / 2) + (stationRect.width / 2);

  gameTable.scrollTo({
    left: scrollOffset,
    behavior: 'smooth'
  });
}

function truncateText(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}
