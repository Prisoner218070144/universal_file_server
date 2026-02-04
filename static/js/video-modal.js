// Enhanced Video Modal functionality with complete controls
let currentVideoPath = '';
let videoPlayer = null;
let playlist = [];
let currentPlaylistIndex = -1;
let subtitleTracks = [];
let audioTracks = [];
let savedVideoPositions = {};
let videoControlsVisible = true;
let customSubtitleFile = null;

// Initialize video modal
function initVideoModal() {
    const modal = document.getElementById('videoModal');
    if (!modal) return;
    
    const closeBtn = modal.querySelector('.close');
    
    if (closeBtn) {
        closeBtn.onclick = closeVideoModal;
    }
    
    // Get video player element
    videoPlayer = document.getElementById('modalVideoPlayer');
    
    if (videoPlayer) {
        // Setup event listeners
        setupVideoPlayerEvents();
        
        // Initialize custom controls
        initCustomControls();
        
        // Load saved video positions
        loadSavedPositions();
        
        // Check for saved settings
        loadVideoSettings();
    }
}

function setupVideoPlayerEvents() {
    if (!videoPlayer) return;
    
    videoPlayer.addEventListener('loadedmetadata', function() {
        updateVideoInfo();
        updateDurationDisplay();
        updateSeekSliderMax();
        
        // Restore saved position if available
        if (savedVideoPositions[currentVideoPath]) {
            videoPlayer.currentTime = savedVideoPositions[currentVideoPath];
        }
    });
    
    videoPlayer.addEventListener('timeupdate', function() {
        updateTimeDisplay();
        updateSeekSlider();
        
        // Save position every 5 seconds
        if (Math.floor(videoPlayer.currentTime) % 5 === 0) {
            saveVideoPosition();
        }
    });
    
    videoPlayer.addEventListener('ended', function() {
        const autoPlayNext = document.getElementById('autoPlayNext')?.checked || false;
        if (autoPlayNext && playlist.length > 0) {
            playNextVideo();
        }
    });
    
    videoPlayer.addEventListener('volumechange', function() {
        updateVolumeControls();
    });
    
    videoPlayer.addEventListener('play', function() {
        updatePlayPauseButton(true);
    });
    
    videoPlayer.addEventListener('pause', function() {
        updatePlayPauseButton(false);
    });
    
    videoPlayer.addEventListener('error', function(e) {
        console.error('Video playback error:', videoPlayer.error);
        handleVideoError(videoPlayer.error);
    });
}

function initCustomControls() {
    if (!videoPlayer) return;
    
    // Initialize seek slider
    const seekSlider = document.getElementById('seekSlider');
    if (seekSlider) {
        seekSlider.addEventListener('mousedown', function() {
            videoPlayer.removeEventListener('timeupdate', updateSeekSlider);
        });
        
        seekSlider.addEventListener('mouseup', function() {
            videoPlayer.addEventListener('timeupdate', updateSeekSlider);
            seekVideo(this.value);
        });
    }
    
    // Initialize volume slider
    const volumeSlider = document.getElementById('volumeSlider');
    if (volumeSlider) {
        volumeSlider.addEventListener('input', function() {
            setVolume(this.value);
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleVideoKeyboardShortcuts);
}

function handleVideoKeyboardShortcuts(e) {
    // Only handle shortcuts when video modal is open
    const modal = document.getElementById('videoModal');
    if (!modal || modal.style.display !== 'block') return;
    
    // Don't trigger shortcuts when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    e.preventDefault();
    
    switch(e.key.toLowerCase()) {
        case ' ':
        case 'k':
            togglePlayPause();
            break;
        case 'f':
            toggleFullscreen();
            break;
        case 'm':
            toggleMute();
            break;
        case 'arrowleft':
            if (e.ctrlKey) {
                seekRelative(-60);
            } else if (e.shiftKey) {
                seekRelative(-10);
            } else {
                seekRelative(-5);
            }
            break;
        case 'arrowright':
            if (e.ctrlKey) {
                seekRelative(60);
            } else if (e.shiftKey) {
                seekRelative(10);
            } else {
                seekRelative(5);
            }
            break;
        case 'escape':
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                closeVideoModal();
            }
            break;
    }
}

function openVideoModal(path, filename, event = null) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    console.log('Opening video modal for:', path, filename);
    
    const modal = document.getElementById('videoModal');
    if (!modal) {
        console.error('Video modal not found');
        // Fallback: open in stream
        const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
        window.open('/stream/' + encodedPath, '_blank');
        return;
    }
    
    // Save current path
    currentVideoPath = path;
    
    // Set video info
    const videoTitle = document.getElementById('videoTitle');
    const videoFileName = document.getElementById('videoFileName');
    if (videoTitle) videoTitle.textContent = filename;
    if (videoFileName) videoFileName.textContent = filename;
    
    // Set video source
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    
    if (!videoPlayer) {
        videoPlayer = document.getElementById('modalVideoPlayer');
        if (!videoPlayer) {
            console.error('Video player not found');
            return;
        }
    }
    
    videoPlayer.src = '/stream/' + encodedPath;
    videoPlayer.setAttribute('data-file-path', path);
    
    // Show modal
    modal.style.display = 'block';
    
    // Focus the video player for keyboard shortcuts
    videoPlayer.focus();
    
    // Load video info
    fetchVideoInfo(path);
    
    // Load playlist
    loadModalPlaylist(path);
    
    // Reset and prepare video
    videoPlayer.load();
    
    // Attempt to play (with error handling)
    const playPromise = videoPlayer.play();
    if (playPromise !== undefined) {
        playPromise.catch(error => {
            console.log('Auto-play prevented:', error);
            // Show play button
            updatePlayPauseButton(false);
        });
    }
}

function fetchVideoInfo(path) {
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    
    fetch('/file/' + encodedPath, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                const size = response.headers.get('content-length');
                if (size) {
                    document.getElementById('videoFileSize').textContent = formatFileSize(parseInt(size));
                }
                
                // Get file extension for format
                const format = path.split('.').pop().toUpperCase();
                document.getElementById('videoFormat').textContent = format;
            }
        })
        .catch(error => {
            console.error('Error loading video info:', error);
        });
}

// Playback Controls
function togglePlayPause() {
    if (!videoPlayer) return;
    
    if (videoPlayer.paused) {
        videoPlayer.play();
    } else {
        videoPlayer.pause();
    }
}

function updatePlayPauseButton(isPlaying) {
    const btn = document.getElementById('playPauseBtn');
    if (btn) {
        btn.textContent = isPlaying ? '⏸️' : '▶️';
    }
}

function toggleMute() {
    if (!videoPlayer) return;
    
    videoPlayer.muted = !videoPlayer.muted;
    updateMuteButton();
}

function updateMuteButton() {
    if (!videoPlayer) return;
    
    const btn = document.getElementById('muteBtn');
    if (btn) {
        btn.textContent = videoPlayer.muted ? '🔇' : 
                         videoPlayer.volume === 0 ? '🔇' : 
                         videoPlayer.volume < 0.5 ? '🔈' : '🔊';
    }
}

function setVolume(value) {
    if (!videoPlayer) return;
    
    videoPlayer.volume = value / 100;
    updateVolumeControls();
}

function updateVolumeControls() {
    if (!videoPlayer) return;
    
    const slider = document.getElementById('volumeSlider');
    if (slider) {
        slider.value = videoPlayer.volume * 100;
    }
    updateMuteButton();
}

// Seek Controls
function seekVideo(value) {
    if (!videoPlayer || !videoPlayer.duration) return;
    
    const percentage = value / 100;
    videoPlayer.currentTime = percentage * videoPlayer.duration;
}

function seekRelative(seconds) {
    if (!videoPlayer) return;
    
    videoPlayer.currentTime += seconds;
}

function updateSeekSlider() {
    if (!videoPlayer || !videoPlayer.duration) return;
    
    const slider = document.getElementById('seekSlider');
    if (slider) {
        const percentage = (videoPlayer.currentTime / videoPlayer.duration) * 100;
        slider.value = percentage;
    }
}

function updateSeekSliderMax() {
    const slider = document.getElementById('seekSlider');
    if (slider) {
        slider.max = 100;
    }
}

// Time Display
function updateTimeDisplay() {
    if (!videoPlayer) return;
    
    const current = document.getElementById('currentTime');
    if (current) {
        current.textContent = formatTime(videoPlayer.currentTime);
    }
}

function updateDurationDisplay() {
    if (!videoPlayer) return;
    
    const duration = document.getElementById('durationTime');
    if (duration) {
        duration.textContent = formatTime(videoPlayer.duration);
    }
}

function updateVideoInfo() {
    if (!videoPlayer) return;
    
    const duration = document.getElementById('videoDuration');
    if (duration) {
        duration.textContent = formatTime(videoPlayer.duration);
    }
}

// Playlist Functions
function loadModalPlaylist(currentVideoPath) {
    const dirPath = currentVideoPath.substring(0, currentVideoPath.lastIndexOf('/'));
    let url = '/get_directory_files/';
    if (dirPath) {
        url = '/get_directory_files/' + encodeURIComponent(dirPath);
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.files) {
                playlist = data.files.filter(file => file.type === 'video');
                currentPlaylistIndex = playlist.findIndex(file => file.path === currentVideoPath);
                renderPlaylist();
            }
        })
        .catch(error => {
            console.error('Error loading playlist:', error);
        });
}

function renderPlaylist() {
    const playlistItems = document.getElementById('modalPlaylistItems');
    if (!playlistItems) return;
    
    playlistItems.innerHTML = '';
    
    if (playlist.length === 0) {
        playlistItems.innerHTML = '<div class="no-videos">No videos in this folder</div>';
        return;
    }
    
    playlist.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = `playlist-item ${index === currentPlaylistIndex ? 'active' : ''}`;
        item.innerHTML = `
            <span class="playlist-index">${index + 1}</span>
            <span class="playlist-title" title="${file.name}">${truncateText(file.name, 30)}</span>
            <span class="playlist-duration">${file.size}</span>
        `;
        item.onclick = () => {
            playVideoFromPlaylist(index);
        };
        playlistItems.appendChild(item);
    });
}

function playVideoFromPlaylist(index) {
    if (index >= 0 && index < playlist.length) {
        const video = playlist[index];
        currentPlaylistIndex = index;
        openVideoModal(video.path, video.name);
        renderPlaylist();
    }
}

function playNextVideo() {
    if (currentPlaylistIndex < playlist.length - 1) {
        playVideoFromPlaylist(currentPlaylistIndex + 1);
    }
}

function playPreviousVideo() {
    if (currentPlaylistIndex > 0) {
        playVideoFromPlaylist(currentPlaylistIndex - 1);
    }
}

// Fullscreen
function toggleFullscreen() {
    const wrapper = document.getElementById('modalVideoWrapper');
    if (!wrapper) return;
    
    if (!document.fullscreenElement) {
        if (wrapper.requestFullscreen) {
            wrapper.requestFullscreen();
        } else if (wrapper.webkitRequestFullscreen) {
            wrapper.webkitRequestFullscreen();
        } else if (wrapper.msRequestFullscreen) {
            wrapper.msRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

// Save/Load Positions
function saveVideoPosition() {
    if (!videoPlayer || !document.getElementById('rememberPosition')?.checked) return;
    
    savedVideoPositions[currentVideoPath] = videoPlayer.currentTime;
    localStorage.setItem('videoPositions', JSON.stringify(savedVideoPositions));
}

function loadSavedPositions() {
    const saved = localStorage.getItem('videoPositions');
    if (saved) {
        try {
            savedVideoPositions = JSON.parse(saved);
        } catch (e) {
            savedVideoPositions = {};
        }
    }
}

function loadVideoSettings() {
    const autoPlayNext = localStorage.getItem('videoAutoPlayNext') !== 'false';
    const loopVideo = localStorage.getItem('videoLoop') === 'true';
    const rememberPosition = localStorage.getItem('videoRememberPosition') !== 'false';
    
    const autoPlayNextCheckbox = document.getElementById('autoPlayNext');
    const loopVideoCheckbox = document.getElementById('loopVideo');
    const rememberPositionCheckbox = document.getElementById('rememberPosition');
    
    if (autoPlayNextCheckbox) autoPlayNextCheckbox.checked = autoPlayNext;
    if (loopVideoCheckbox) loopVideoCheckbox.checked = loopVideo;
    if (rememberPositionCheckbox) rememberPositionCheckbox.checked = rememberPosition;
    
    if (videoPlayer) {
        videoPlayer.loop = loopVideo;
    }
}

function handleVideoError(error) {
    console.error('Video error:', error);
    
    let errorMessage = 'Video playback error. ';
    
    if (error) {
        switch(error.code) {
            case 1:
                errorMessage += 'The video was aborted.';
                break;
            case 2:
                errorMessage += 'Network error. Please check your connection.';
                break;
            case 3:
                errorMessage += 'Error decoding video. The format may not be supported by your browser.';
                break;
            case 4:
                errorMessage += 'Video format not supported. Try downloading the file instead.';
                break;
            default:
                errorMessage += 'Unknown error. Try downloading the file or using a different browser.';
        }
    }
    
    // Show error in UI
    const errorDiv = document.createElement('div');
    errorDiv.className = 'video-error';
    errorDiv.innerHTML = `
        <h4>⚠️ Playback Error</h4>
        <p>${errorMessage}</p>
        <div class="error-actions">
            <button onclick="tryPlayVideo()" class="btn-warning">Try Again</button>
            <button onclick="downloadCurrentVideo()" class="btn-secondary">Download Video</button>
        </div>
    `;
    
    const videoWrapper = document.getElementById('modalVideoWrapper');
    if (videoWrapper) {
        // Remove existing error if any
        const existingError = videoWrapper.querySelector('.video-error');
        if (existingError) existingError.remove();
        
        videoWrapper.appendChild(errorDiv);
    }
}

function tryPlayVideo() {
    const errorDiv = document.querySelector('.video-error');
    if (errorDiv) errorDiv.remove();
    
    if (videoPlayer && currentVideoPath) {
        const encodedPath = encodeURIComponent(currentVideoPath).replace(/%2F/g, '/');
        videoPlayer.src = '/stream/' + encodedPath;
        videoPlayer.load();
        
        videoPlayer.play().catch(error => {
            console.error('Retry failed:', error);
            handleVideoError(error);
        });
    }
}

function downloadCurrentVideo() {
    if (currentVideoPath) {
        window.location.href = '/download/' + encodeURIComponent(currentVideoPath);
    }
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    if (modal) {
        modal.style.display = 'none';
    }
    currentVideoPath = '';
    playlist = [];
    currentPlaylistIndex = -1;
}

// Utility Functions
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

// Export functions
window.openVideoModal = openVideoModal;
window.closeVideoModal = closeVideoModal;
window.togglePlayPause = togglePlayPause;
window.toggleMute = toggleMute;
window.setVolume = setVolume;
window.seekVideo = seekVideo;
window.seekRelative = seekRelative;
window.toggleFullscreen = toggleFullscreen;
window.playNextVideo = playNextVideo;
window.playPreviousVideo = playPreviousVideo;
window.tryPlayVideo = tryPlayVideo;
window.downloadCurrentVideo = downloadCurrentVideo;
window.togglePlaylist = function() {
    const playlist = document.getElementById('modalPlaylistSection');
    if (playlist) {
        playlist.style.display = playlist.style.display === 'none' ? 'flex' : 'none';
    }
};