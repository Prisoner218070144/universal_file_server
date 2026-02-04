// Clipboard functionality for copy, paste, move, undo

// Global clipboard state
let clipboard = {
    action: null, // 'copy' or 'cut'
    path: null,
    name: null,
    type: null
};

let actionHistory = [];
let MAX_HISTORY = 50;

// Initialize clipboard from localStorage
function initClipboard() {
    const saved = localStorage.getItem('fileServerClipboard');
    if (saved) {
        try {
            clipboard = JSON.parse(saved);
            updateClipboardUI();
        } catch (e) {
            console.error('Failed to load clipboard:', e);
        }
    }
    
    const savedHistory = localStorage.getItem('fileServerActionHistory');
    if (savedHistory) {
        try {
            actionHistory = JSON.parse(savedHistory);
            updateUndoUI();
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }
}

// Save clipboard to localStorage
function saveClipboard() {
    localStorage.setItem('fileServerClipboard', JSON.stringify(clipboard));
    updateClipboardUI();
}

// Save history to localStorage
function saveActionHistory() {
    // Keep only last MAX_HISTORY items
    if (actionHistory.length > MAX_HISTORY) {
        actionHistory = actionHistory.slice(-MAX_HISTORY);
    }
    localStorage.setItem('fileServerActionHistory', JSON.stringify(actionHistory));
    updateUndoUI();
}

// Copy item to clipboard
function copyToClipboard(path, type, name = null) {
    if (!name) {
        name = path.split('/').pop();
    }
    
    clipboard = {
        action: 'copy',
        path: path,
        name: name,
        type: type
    };
    
    saveClipboard();
    showToast(`"${name}" copied to clipboard`, 'success');
}

// Cut item to clipboard
function cutToClipboard(path, type, name = null) {
    if (!name) {
        name = path.split('/').pop();
    }
    
    clipboard = {
        action: 'cut',
        path: path,
        name: name,
        type: type
    };
    
    saveClipboard();
    showToast(`"${name}" cut to clipboard`, 'success');
}

// Paste from clipboard
function pasteFromClipboard() {
    if (!clipboard.path) {
        showToast('Clipboard is empty', 'error');
        return;
    }
    
    const currentPath = document.body.getAttribute('data-current-path') || '';
    showMoveCopyModal(clipboard.action, currentPath);
}

// Show move/copy modal
function showMoveCopyModal(action, destinationPath = '') {
    const modal = document.getElementById('moveCopyModal');
    const title = document.getElementById('moveCopyTitle');
    const pathInput = document.getElementById('destinationPath');
    const confirmBtn = document.getElementById('confirmMoveCopyBtn');
    
    if (!modal) return;
    
    const actionText = action === 'copy' ? 'Copy' : 'Move';
    title.textContent = `${actionText} "${clipboard.name}"`;
    pathInput.value = destinationPath;
    confirmBtn.textContent = actionText;
    
    modal.style.display = 'block';
}

// Close move/copy modal
function closeMoveCopyModal() {
    const modal = document.getElementById('moveCopyModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Confirm move/copy action
function confirmMoveCopy() {
    const destinationPath = document.getElementById('destinationPath').value.trim();
    const overwrite = document.getElementById('overwriteExisting').checked;
    
    if (!destinationPath) {
        showToast('Please enter destination path', 'error');
        return;
    }
    
    closeMoveCopyModal();
    
    // Save original action for undo
    const originalAction = {
        action: clipboard.action,
        source: clipboard.path,
        destination: destinationPath,
        timestamp: new Date().toISOString()
    };
    
    // Perform the action
    if (clipboard.action === 'copy') {
        copyFileOrFolder(clipboard.path, destinationPath, overwrite, originalAction);
    } else if (clipboard.action === 'cut') {
        moveFileOrFolder(clipboard.path, destinationPath, overwrite, originalAction);
    }
}

// Copy file or folder
function copyFileOrFolder(source, destination, overwrite = false, originalAction = null) {
    const payload = {
        source: source,
        destination: destination,
        overwrite: overwrite
    };
    
    fetch('/copy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`"${clipboard.name}" copied successfully`, 'success');
            
            // Add to history
            if (originalAction) {
                actionHistory.push({
                    ...originalAction,
                    undoAction: 'delete',
                    undoDestination: data.new_path
                });
                saveActionHistory();
            }
            
            // Clear clipboard if cut operation
            if (clipboard.action === 'cut') {
                clipboard = { action: null, path: null, name: null, type: null };
                saveClipboard();
            }
            
            // Reload page after delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(`Copy failed: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        showToast('Copy failed: Network error', 'error');
        console.error('Copy error:', error);
    });
}

// Move file or folder
function moveFileOrFolder(source, destination, overwrite = false, originalAction = null) {
    const payload = {
        source: source,
        destination: destination,
        overwrite: overwrite
    };
    
    fetch('/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`"${clipboard.name}" moved successfully`, 'success');
            
            // Add to history
            if (originalAction) {
                actionHistory.push({
                    ...originalAction,
                    undoAction: 'move',
                    undoDestination: source
                });
                saveActionHistory();
            }
            
            // Clear clipboard
            clipboard = { action: null, path: null, name: null, type: null };
            saveClipboard();
            
            // Reload page after delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(`Move failed: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        showToast('Move failed: Network error', 'error');
        console.error('Move error:', error);
    });
}

// Undo last action
function undoLastAction() {
    if (actionHistory.length === 0) {
        showToast('No actions to undo', 'info');
        return;
    }
    
    const lastAction = actionHistory.pop();
    
    if (lastAction.undoAction === 'delete') {
        // Undo copy by deleting the copied file
        fetch('/delete/' + encodeURIComponent(lastAction.undoDestination), {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Undo successful', 'success');
                saveActionHistory();
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                showToast(`Undo failed: ${data.error}`, 'error');
                actionHistory.push(lastAction); // Restore to history
            }
        })
        .catch(error => {
            showToast('Undo failed: Network error', 'error');
            actionHistory.push(lastAction); // Restore to history
        });
    } else if (lastAction.undoAction === 'move') {
        // Undo move by moving back
        moveFileOrFolder(lastAction.destination, lastAction.undoDestination, true, null);
    }
}

// Update clipboard UI
function updateClipboardUI() {
    const pasteBtn = document.getElementById('pasteBtn');
    if (pasteBtn) {
        pasteBtn.disabled = !clipboard.path;
    }
    
    // Update clipboard indicator in header
    const clipboardIndicator = document.getElementById('clipboardIndicator');
    if (!clipboardIndicator) {
        // Create indicator if it doesn't exist
        const headerActions = document.querySelector('.header-actions');
        if (headerActions && clipboard.path) {
            const indicator = document.createElement('div');
            indicator.id = 'clipboardIndicator';
            indicator.className = 'clipboard-indicator';
            indicator.innerHTML = `
                <span>📋 ${clipboard.action === 'copy' ? 'Copy:' : 'Cut:'} ${clipboard.name}</span>
                <button onclick="clearClipboard()" class="btn-clear-clipboard">×</button>
            `;
            headerActions.appendChild(indicator);
        }
    } else if (clipboard.path) {
        clipboardIndicator.innerHTML = `
            <span>📋 ${clipboard.action === 'copy' ? 'Copy:' : 'Cut:'} ${clipboard.name}</span>
            <button onclick="clearClipboard()" class="btn-clear-clipboard">×</button>
        `;
        clipboardIndicator.style.display = 'flex';
    } else {
        clipboardIndicator.style.display = 'none';
    }
}

// Update undo UI
function updateUndoUI() {
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.disabled = actionHistory.length === 0;
    }
}

// Clear clipboard
function clearClipboard() {
    clipboard = { action: null, path: null, name: null, type: null };
    saveClipboard();
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</span>
        <span class="toast-message">${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Video modal functions
function togglePlaylist() {
    const playlist = document.getElementById('modalPlaylistSection');
    playlist.style.display = playlist.style.display === 'none' ? 'flex' : 'none';
}

function toggleFullscreen() {
    const videoPlayer = document.getElementById('modalVideoPlayer');
    if (!document.fullscreenElement) {
        if (videoPlayer.requestFullscreen) {
            videoPlayer.requestFullscreen();
        } else if (videoPlayer.webkitRequestFullscreen) {
            videoPlayer.webkitRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        }
    }
}

function downloadCurrentVideo() {
    const videoPath = document.getElementById('modalVideoPlayer').getAttribute('data-file-path');
    if (videoPath) {
        window.location.href = '/download/' + encodeURIComponent(videoPath);
    }
}

function setModalAspectRatio(ratio) {
    const wrapper = document.getElementById('modalVideoWrapper');
    switch(ratio) {
        case '16:9':
            wrapper.style.aspectRatio = '16/9';
            break;
        case '4:3':
            wrapper.style.aspectRatio = '4/3';
            break;
        case '1:1':
            wrapper.style.aspectRatio = '1/1';
            break;
        case 'original':
            wrapper.style.aspectRatio = 'auto';
            break;
    }
}

function modalZoomVideo(factor) {
    const video = document.getElementById('modalVideoPlayer');
    const currentZoom = parseFloat(video.style.transform.replace('scale(', '').replace(')', '')) || 1;
    const newZoom = currentZoom * factor;
    video.style.transform = `scale(${newZoom})`;
    updateZoomSelect(newZoom);
}

function modalResetVideo() {
    const video = document.getElementById('modalVideoPlayer');
    video.style.transform = 'scale(1)';
    updateZoomSelect(1);
}

function modalSetZoom(value) {
    const video = document.getElementById('modalVideoPlayer');
    video.style.transform = `scale(${value})`;
}

function updateZoomSelect(value) {
    const select = document.getElementById('zoomLevel');
    if (select) {
        select.value = value.toString();
    }
}

function setPlaybackSpeed(value) {
    const video = document.getElementById('modalVideoPlayer');
    if (video) {
        video.playbackRate = parseFloat(value);
    }
}

function loadSubtitle(value) {
    if (value === 'upload') {
        document.getElementById('subtitleFile').click();
    } else {
        // Handle built-in subtitles
        const subtitleTrack = document.getElementById('subtitleTrack');
        subtitleTrack.style.display = 'none';
    }
}

function handleSubtitleUpload(file) {
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        // Parse SRT or VTT and display subtitles
        displaySubtitles(e.target.result);
    };
    reader.readAsText(file);
}

function displaySubtitles(srtContent) {
    // Simple SRT parser
    const lines = srtContent.split('\n');
    let currentSub = '';
    let inSubtitle = false;
    
    const subtitleTrack = document.getElementById('subtitleTrack');
    subtitleTrack.style.display = 'block';
    
    // This is a simplified version - in production you'd want a proper SRT parser
    for (const line of lines) {
        if (line.includes('-->')) {
            inSubtitle = true;
            currentSub = '';
        } else if (line.trim() === '' && inSubtitle) {
            inSubtitle = false;
            // Here you would set up timing for the subtitle
        } else if (inSubtitle && line.trim()) {
            currentSub += line + '<br>';
        }
    }
    
    subtitleTrack.innerHTML = currentSub;
}

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
                const playlistItems = document.getElementById('modalPlaylistItems');
                playlistItems.innerHTML = '';
                
                // Filter only video files
                const videoFiles = data.files.filter(file => file.type === 'video');
                
                if (videoFiles.length === 0) {
                    playlistItems.innerHTML = '<div class="no-videos">No other videos in this folder</div>';
                    return;
                }
                
                videoFiles.forEach((file, index) => {
                    const item = document.createElement('div');
                    item.className = `playlist-item ${file.path === currentVideoPath ? 'active' : ''}`;
                    item.innerHTML = `
                        <span class="playlist-index">${index + 1}</span>
                        <span class="playlist-title">${file.name}</span>
                        <span class="playlist-duration">${file.size}</span>
                    `;
                    item.onclick = () => {
                        // Switch to this video
                        const videoPlayer = document.getElementById('modalVideoPlayer');
                        const encodedPath = encodeURIComponent(file.path).replace(/%2F/g, '/');
                        videoPlayer.src = '/stream/' + encodedPath;
                        videoPlayer.setAttribute('data-file-path', file.path);
                        document.getElementById('videoFileName').textContent = file.name;
                        
                        // Update active item
                        document.querySelectorAll('.playlist-item').forEach(i => i.classList.remove('active'));
                        item.classList.add('active');
                    };
                    playlistItems.appendChild(item);
                });
            }
        })
        .catch(error => {
            console.error('Error loading playlist:', error);
            document.getElementById('modalPlaylistItems').innerHTML = '<div class="error-loading">Error loading playlist</div>';
        });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initClipboard();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Don't trigger when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'c':
                    e.preventDefault();
                    // Copy currently selected item
                    const selected = document.querySelector('.file-item.selected');
                    if (selected) {
                        const path = selected.getAttribute('data-path');
                        const type = selected.getAttribute('data-type');
                        const name = selected.getAttribute('data-name');
                        if (path && type) {
                            copyToClipboard(path, type, name);
                        }
                    }
                    break;
                case 'x':
                    e.preventDefault();
                    // Cut currently selected item
                    const selectedForCut = document.querySelector('.file-item.selected');
                    if (selectedForCut) {
                        const path = selectedForCut.getAttribute('data-path');
                        const type = selectedForCut.getAttribute('data-type');
                        const name = selectedForCut.getAttribute('data-name');
                        if (path && type) {
                            cutToClipboard(path, type, name);
                        }
                    }
                    break;
                case 'v':
                    e.preventDefault();
                    pasteFromClipboard();
                    break;
                case 'z':
                    e.preventDefault();
                    undoLastAction();
                    break;
            }
        }
    });
    
    // Close modals when clicking outside
    window.onclick = function(event) {
        const modal = document.getElementById('moveCopyModal');
        if (event.target == modal) {
            closeMoveCopyModal();
        }
    };
});

// Export functions for HTML onclick
window.copyToClipboard = copyToClipboard;
window.cutToClipboard = cutToClipboard;
window.pasteFromClipboard = pasteFromClipboard;
window.undoLastAction = undoLastAction;
window.showMoveCopyModal = showMoveCopyModal;
window.closeMoveCopyModal = closeMoveCopyModal;
window.confirmMoveCopy = confirmMoveCopy;
window.togglePlaylist = togglePlaylist;
window.toggleFullscreen = toggleFullscreen;
window.downloadCurrentVideo = downloadCurrentVideo;
window.setModalAspectRatio = setModalAspectRatio;
window.modalZoomVideo = modalZoomVideo;
window.modalResetVideo = modalResetVideo;
window.modalSetZoom = modalSetZoom;
window.setPlaybackSpeed = setPlaybackSpeed;
window.loadSubtitle = loadSubtitle;
window.handleSubtitleUpload = handleSubtitleUpload;