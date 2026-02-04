// Audio Modal functionality
let currentAudioPath = '';
let audioPlayer = null;
let audioPlaylist = [];
let currentAudioIndex = -1;
let savedAudioPositions = {};

// Initialize audio modal
function initAudioModal() {
    const modal = document.getElementById('audioModal');
    if (!modal) return;
    
    const closeBtn = modal.querySelector('.close');
    if (closeBtn) {
        closeBtn.onclick = closeAudioModal;
    }
    
    window.onclick = function(event) {
        if (event.target == modal) {
            closeAudioModal();
        }
    };
    
    // Get audio player element
    audioPlayer = document.getElementById('modalAudioPlayer');
    
    if (audioPlayer) {
        // Setup event listeners
        setupAudioPlayerEvents();
        
        // Initialize custom controls
        initAudioCustomControls();
        
        // Load saved audio positions
        loadSavedAudioPositions();
        
        // Check for saved settings
        loadAudioSettings();
    }
}

function setupAudioPlayerEvents() {
    audioPlayer.addEventListener('loadedmetadata', function() {
        updateAudioInfo();
        updateAudioDurationDisplay();
        
        // Restore saved position if available
        if (savedAudioPositions[currentAudioPath]) {
            audioPlayer.currentTime = savedAudioPositions[currentAudioPath];
        }
    });
    
    audioPlayer.addEventListener('timeupdate', function() {
        updateAudioTimeDisplay();
        updateAudioSeekSlider();
        
        // Save position every 5 seconds
        if (Math.floor(audioPlayer.currentTime) % 5 === 0) {
            saveAudioPosition();
        }
    });
    
    audioPlayer.addEventListener('ended', function() {
        const autoPlayNext = document.getElementById('audioAutoPlayNext').checked;
        if (autoPlayNext && audioPlaylist.length > 0) {
            playNextAudio();
        }
    });
    
    audioPlayer.addEventListener('volumechange', function() {
        updateAudioVolumeControls();
    });
    
    audioPlayer.addEventListener('play', function() {
        updateAudioPlayPauseButton(true);
    });
    
    audioPlayer.addEventListener('pause', function() {
        updateAudioPlayPauseButton(false);
    });
    
    audioPlayer.addEventListener('error', function(e) {
        console.error('Audio playback error:', audioPlayer.error);
        handleAudioError(audioPlayer.error);
    });
}

function initAudioCustomControls() {
    // Initialize seek slider
    const seekSlider = document.getElementById('audioSeekSlider');
    if (seekSlider) {
        seekSlider.addEventListener('mousedown', function() {
            audioPlayer.removeEventListener('timeupdate', updateAudioSeekSlider);
        });
        
        seekSlider.addEventListener('mouseup', function() {
            audioPlayer.addEventListener('timeupdate', updateAudioSeekSlider);
            seekAudio(this.value);
        });
    }
    
    // Initialize volume slider
    const volumeSlider = document.getElementById('audioVolumeSlider');
    if (volumeSlider) {
        volumeSlider.addEventListener('input', function() {
            setAudioVolume(this.value);
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleAudioKeyboardShortcuts);
}

function handleAudioKeyboardShortcuts(e) {
    // Only handle shortcuts when audio modal is open
    const modal = document.getElementById('audioModal');
    if (!modal || modal.style.display !== 'block') return;
    
    // Don't trigger shortcuts when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    e.preventDefault();
    
    switch(e.key.toLowerCase()) {
        case ' ':
        case 'k':
            toggleAudioPlayPause();
            break;
        case 'm':
            toggleAudioMute();
            break;
        case 'arrowleft':
            if (e.ctrlKey) {
                seekAudioRelative(-60); // Jump back 1 minute
            } else if (e.shiftKey) {
                seekAudioRelative(-10); // Jump back 10 seconds
            } else {
                seekAudioRelative(-5); // Jump back 5 seconds
            }
            break;
        case 'arrowright':
            if (e.ctrlKey) {
                seekAudioRelative(60); // Jump forward 1 minute
            } else if (e.shiftKey) {
                seekAudioRelative(10); // Jump forward 10 seconds
            } else {
                seekAudioRelative(5); // Jump forward 5 seconds
            }
            break;
        case 'arrowup':
            adjustAudioVolume(10);
            break;
        case 'arrowdown':
            adjustAudioVolume(-10);
            break;
        case '0':
        case 'home':
            audioPlayer.currentTime = 0;
            break;
        case 'end':
            audioPlayer.currentTime = audioPlayer.duration;
            break;
        case 'escape':
            closeAudioModal();
            break;
        case 'n':
            playNextAudio();
            break;
        case 'p':
            playPreviousAudio();
            break;
    }
}

function openAudioModal(path, filename) {
    event.stopPropagation();
    
    const modal = document.getElementById('audioModal');
    if (!modal || !audioPlayer) {
        // Fallback: open in new tab
        const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
        window.open('/stream/' + encodedPath, '_blank');
        return;
    }
    
    // Save current path
    currentAudioPath = path;
    
    // Set audio info
    document.getElementById('audioTitle').textContent = filename;
    document.getElementById('audioFileName').textContent = filename;
    
    // Set audio source
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    audioPlayer.src = '/stream/' + encodedPath;
    
    // Reset audio state
    resetAudioSettings();
    
    // Load playlist
    loadAudioPlaylist(path);
    
    // Show modal
    modal.style.display = 'block';
    
    // Focus the audio player for keyboard shortcuts
    audioPlayer.focus();
    
    // Load audio info
    fetchAudioInfo(path);
}

function resetAudioSettings() {
    audioPlayer.playbackRate = 1;
    
    // Reset UI elements
    document.querySelectorAll('.audio-speed-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector('.audio-speed-btn[onclick="setAudioPlaybackSpeed(1)"]').classList.add('active');
}

function fetchAudioInfo(path) {
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    
    fetch('/file/' + encodedPath, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                const size = response.headers.get('content-length');
                document.getElementById('audioFileSize').textContent = 
                    formatFileSize(size) || 'Unknown';
                
                // Get file extension for format
                const format = path.split('.').pop().toUpperCase();
                document.getElementById('audioFormat').textContent = format;
            }
        })
        .catch(error => {
            console.error('Error loading audio info:', error);
        });
}

function updateAudioInfo() {
    if (!audioPlayer) return;
    
    // Update duration
    const duration = formatTime(audioPlayer.duration);
    document.getElementById('audioDuration').textContent = duration;
    document.getElementById('audioDurationTime').textContent = duration;
    
    // Calculate bitrate if possible
    if (audioPlayer.duration > 0) {
        const size = parseInt(audioPlayer.getAttribute('data-size') || '0');
        if (size > 0) {
            const bitrate = Math.round((size * 8) / audioPlayer.duration / 1000); // kbps
            document.getElementById('audioBitrate').textContent = `${bitrate} kbps`;
        }
    }
}

// Playback Controls
function toggleAudioPlayPause() {
    if (audioPlayer.paused) {
        audioPlayer.play();
    } else {
        audioPlayer.pause();
    }
}

function updateAudioPlayPauseButton(isPlaying) {
    const btn = document.getElementById('audioPlayPauseBtn');
    if (btn) {
        btn.textContent = isPlaying ? '⏸️' : '▶️';
    }
}

function toggleAudioMute() {
    audioPlayer.muted = !audioPlayer.muted;
    updateAudioMuteButton();
}

function updateAudioMuteButton() {
    const btn = document.getElementById('audioMuteBtn');
    if (btn) {
        btn.textContent = audioPlayer.muted ? '🔇' : 
                         audioPlayer.volume === 0 ? '🔇' : 
                         audioPlayer.volume < 0.5 ? '🔈' : '🔊';
    }
}

function setAudioVolume(value) {
    audioPlayer.volume = value / 100;
    updateAudioVolumeControls();
}

function adjustAudioVolume(change) {
    const newVolume = Math.min(100, Math.max(0, audioPlayer.volume * 100 + change));
    setAudioVolume(newVolume);
}

function updateAudioVolumeControls() {
    const slider = document.getElementById('audioVolumeSlider');
    if (slider) {
        slider.value = audioPlayer.volume * 100;
    }
    updateAudioMuteButton();
}

// Seek Controls
function seekAudio(value) {
    const percentage = value / 100;
    audioPlayer.currentTime = percentage * audioPlayer.duration;
}

function seekAudioRelative(seconds) {
    audioPlayer.currentTime += seconds;
}

function updateAudioSeekSlider() {
    const slider = document.getElementById('audioSeekSlider');
    if (slider && audioPlayer.duration) {
        const percentage = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        slider.value = percentage;
    }
}

function updateAudioSeekSliderMax() {
    const slider = document.getElementById('audioSeekSlider');
    if (slider) {
        slider.max = 100;
    }
}

// Time Display
function updateAudioTimeDisplay() {
    const current = document.getElementById('audioCurrentTime');
    if (current) {
        current.textContent = formatTime(audioPlayer.currentTime);
    }
}

function updateAudioDurationDisplay() {
    const duration = document.getElementById('audioDurationTime');
    if (duration) {
        duration.textContent = formatTime(audioPlayer.duration);
    }
}

// Playback Speed
function setAudioPlaybackSpeed(speed) {
    audioPlayer.playbackRate = speed;
    
    // Update active speed button
    document.querySelectorAll('.audio-speed-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.audio-speed-btn[onclick="setAudioPlaybackSpeed(${speed})"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}

// Playlist Functions
function loadAudioPlaylist(currentAudioPath) {
    const dirPath = currentAudioPath.substring(0, currentAudioPath.lastIndexOf('/'));
    let url = '/get_directory_files/';
    if (dirPath) {
        url = '/get_directory_files/' + encodeURIComponent(dirPath);
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.files) {
                audioPlaylist = data.files.filter(file => file.type === 'audio');
                currentAudioIndex = audioPlaylist.findIndex(file => file.path === currentAudioPath);
                renderAudioPlaylist();
            }
        })
        .catch(error => {
            console.error('Error loading audio playlist:', error);
        });
}

function renderAudioPlaylist() {
    const playlistItems = document.getElementById('modalAudioPlaylistItems');
    if (!playlistItems) return;
    
    playlistItems.innerHTML = '';
    
    if (audioPlaylist.length === 0) {
        playlistItems.innerHTML = '<div class="no-audios">No audio files in this folder</div>';
        return;
    }
    
    audioPlaylist.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = `playlist-item ${index === currentAudioIndex ? 'active' : ''}`;
        item.innerHTML = `
            <span class="playlist-index">${index + 1}</span>
            <span class="playlist-title" title="${file.name}">${truncateText(file.name, 30)}</span>
            <span class="playlist-duration">${file.size}</span>
            <button class="playlist-remove" onclick="removeFromAudioPlaylist(${index})">×</button>
        `;
        item.onclick = () => {
            playAudioFromPlaylist(index);
        };
        playlistItems.appendChild(item);
    });
}

function playAudioFromPlaylist(index) {
    if (index >= 0 && index < audioPlaylist.length) {
        const audio = audioPlaylist[index];
        currentAudioIndex = index;
        openAudioModal(audio.path, audio.name);
        renderAudioPlaylist();
    }
}

function playNextAudio() {
    if (currentAudioIndex < audioPlaylist.length - 1) {
        playAudioFromPlaylist(currentAudioIndex + 1);
    }
}

function playPreviousAudio() {
    if (currentAudioIndex > 0) {
        playAudioFromPlaylist(currentAudioIndex - 1);
    }
}

function shuffleAudioPlaylist() {
    for (let i = audioPlaylist.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [audioPlaylist[i], audioPlaylist[j]] = [audioPlaylist[j], audioPlaylist[i]];
    }
    currentAudioIndex = audioPlaylist.findIndex(file => file.path === currentAudioPath);
    renderAudioPlaylist();
    showNotification('Playlist shuffled');
}

function clearAudioPlaylist() {
    if (confirm('Clear the playlist?')) {
        audioPlaylist = [];
        currentAudioIndex = -1;
        renderAudioPlaylist();
    }
}

function removeFromAudioPlaylist(index) {
    event.stopPropagation();
    audioPlaylist.splice(index, 1);
    if (currentAudioIndex >= index) {
        currentAudioIndex--;
    }
    renderAudioPlaylist();
}

// Advanced Controls
function toggleAudioAutoPlayNext(checked) {
    localStorage.setItem('audioAutoPlayNext', checked);
}

function toggleAudioLoop(checked) {
    audioPlayer.loop = checked;
    localStorage.setItem('audioLoop', checked);
}

function toggleAudioRememberPosition(checked) {
    localStorage.setItem('audioRememberPosition', checked);
}

function loadAudioSettings() {
    const autoPlayNext = localStorage.getItem('audioAutoPlayNext') !== 'false';
    const loopAudio = localStorage.getItem('audioLoop') === 'true';
    const rememberPosition = localStorage.getItem('audioRememberPosition') !== 'false';
    
    const autoPlayNextElem = document.getElementById('audioAutoPlayNext');
    const loopAudioElem = document.getElementById('audioLoop');
    const rememberPositionElem = document.getElementById('audioRememberPosition');
    
    if (autoPlayNextElem) autoPlayNextElem.checked = autoPlayNext;
    if (loopAudioElem) loopAudioElem.checked = loopAudio;
    if (rememberPositionElem) rememberPositionElem.checked = rememberPosition;
    
    audioPlayer.loop = loopAudio;
}

function saveAudioPosition() {
    if (!document.getElementById('audioRememberPosition') || !document.getElementById('audioRememberPosition').checked) return;
    
    savedAudioPositions[currentAudioPath] = audioPlayer.currentTime;
    localStorage.setItem('audioPositions', JSON.stringify(savedAudioPositions));
}

function loadSavedAudioPositions() {
    const saved = localStorage.getItem('audioPositions');
    if (saved) {
        try {
            savedAudioPositions = JSON.parse(saved);
        } catch (e) {
            savedAudioPositions = {};
        }
    }
}

function showAudioInfo() {
    const info = `
        Audio Information:
        - Current Time: ${formatTime(audioPlayer.currentTime)}
        - Duration: ${formatTime(audioPlayer.duration)}
        - Progress: ${Math.round((audioPlayer.currentTime / audioPlayer.duration) * 100)}%
        - Volume: ${Math.round(audioPlayer.volume * 100)}%
        - Playback Rate: ${audioPlayer.playbackRate}x
        - Audio Codec: ${getAudioCodecInfo()}
    `;
    
    alert(info);
}

function getAudioCodecInfo() {
    const audio = audioPlayer;
    const source = audio.currentSrc || audio.src;
    
    if (source.includes('.mp3')) return 'MPEG Audio Layer 3';
    if (source.includes('.wav')) return 'WAV';
    if (source.includes('.ogg')) return 'Ogg Vorbis';
    if (source.includes('.flac')) return 'FLAC';
    if (source.includes('.m4a')) return 'MPEG-4 Audio';
    if (source.includes('.aac')) return 'AAC';
    
    return 'Unknown';
}

function closeAudioModal() {
    const modal = document.getElementById('audioModal');
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.src = '';
    }
    if (modal) {
        modal.style.display = 'none';
    }
    currentAudioPath = '';
    audioPlaylist = [];
    currentAudioIndex = -1;
}

function handleAudioError(error) {
    const errorCode = error ? error.code : 0;
    let errorMessage = 'Audio playback error. ';
    
    switch(errorCode) {
        case 1:
            errorMessage += 'The audio was aborted.';
            break;
        case 2:
            errorMessage += 'Network error.';
            break;
        case 3:
            errorMessage += 'Error decoding audio.';
            break;
        case 4:
            errorMessage += 'Audio format not supported.';
            break;
        default:
            errorMessage += 'Unknown error.';
    }
    
    // Show error in modal
    const modal = document.getElementById('audioModal');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'audio-error-modal';
    errorDiv.innerHTML = `
        <h4>Playback Error</h4>
        <p>${errorMessage}</p>
        <div class="error-actions">
            <button onclick="tryPlayAudio()" class="btn-warning">Try Again</button>
            <button onclick="downloadCurrentAudio()" class="btn-secondary">Download</button>
            <button onclick="closeAudioModal()" class="btn-secondary">Close</button>
        </div>
    `;
    
    if (modal) {
        modal.querySelector('.audio-modal-main').appendChild(errorDiv);
    }
}

function tryPlayAudio() {
    const errorDiv = document.querySelector('.audio-error-modal');
    if (errorDiv) errorDiv.remove();
    
    if (audioPlayer) {
        audioPlayer.load();
        audioPlayer.play().catch(error => {
            handleAudioError(error);
        });
    }
}

function downloadCurrentAudio() {
    if (currentAudioPath) {
        window.location.href = '/download/' + encodeURIComponent(currentAudioPath);
    }
}

// Utility Functions (shared with video-modal.js)
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'audio-notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #333;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Export functions
window.openAudioModal = openAudioModal;
window.closeAudioModal = closeAudioModal;
window.toggleAudioPlayPause = toggleAudioPlayPause;
window.toggleAudioMute = toggleAudioMute;
window.setAudioVolume = setAudioVolume;
window.seekAudio = seekAudio;
window.seekAudioRelative = seekAudioRelative;
window.setAudioPlaybackSpeed = setAudioPlaybackSpeed;
window.playNextAudio = playNextAudio;
window.playPreviousAudio = playPreviousAudio;
window.shuffleAudioPlaylist = shuffleAudioPlaylist;
window.clearAudioPlaylist = clearAudioPlaylist;
window.removeFromAudioPlaylist = removeFromAudioPlaylist;
window.showAudioInfo = showAudioInfo;
window.toggleAudioAutoPlayNext = toggleAudioAutoPlayNext;
window.toggleAudioLoop = toggleAudioLoop;
window.toggleAudioRememberPosition = toggleAudioRememberPosition;
window.tryPlayAudio = tryPlayAudio;
window.downloadCurrentAudio = downloadCurrentAudio;
window.toggleAudioPlaylist = function() {
    const playlist = document.getElementById('modalAudioPlaylistSection');
    if (playlist) {
        playlist.style.display = playlist.style.display === 'none' ? 'flex' : 'none';
    }
};