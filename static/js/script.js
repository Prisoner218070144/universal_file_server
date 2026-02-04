// Universal File Server - JavaScript
let currentSelection = -1;
let downloadInProgress = false;
let clipboard = {
    action: null, // 'copy' or 'cut'
    path: null,
    name: null,
    type: null
};

let actionHistory = [];

document.addEventListener('DOMContentLoaded', function() {
    // Set focus for keyboard navigation
    document.body.setAttribute('tabindex', '0');
    document.body.focus();
    
    // Initialize keyboard event listeners
    document.addEventListener('keydown', handleKeyPress);
    
    // Add click event listeners to all file items
    const fileItems = document.querySelectorAll('.file-item');
    fileItems.forEach((item, index) => {
        item.addEventListener('click', function(e) {
            if (!e.target.closest('.file-actions')) {
                // Only trigger navigation if not clicking on actions
                clearSelection();
                currentSelection = index;
                this.click();
            }
        });
    });
    
    // Initialize modals
    initVideoModal();
    initDownloadModal();
    initClipboard();
    
    // Focus search box if on search page
    if (window.location.pathname === '/search') {
        const searchBox = document.querySelector('.search-box');
        if (searchBox) {
            searchBox.focus();
            searchBox.select();
        }
    }
});

function handleKeyPress(event) {
    // Don't trigger shortcuts when typing in inputs
    if (event.target.tagName === 'INPUT' || 
        event.target.tagName === 'TEXTAREA' || 
        event.target.tagName === 'SELECT') {
        return;
    }
    
    const fileItems = document.querySelectorAll('.file-item');
    if (fileItems.length === 0) return;
    
    // Handle Ctrl/Command key combinations
    if (event.ctrlKey || event.metaKey) {
        switch(event.key.toLowerCase()) {
            case 'c':
                event.preventDefault();
                copySelected(fileItems);
                break;
            case 'x':
                event.preventDefault();
                cutSelected(fileItems);
                break;
            case 'v':
                event.preventDefault();
                pasteFromClipboard();
                break;
            case 'z':
                event.preventDefault();
                undoLastAction();
                break;
        }
        return;
    }
    
    switch(event.key.toLowerCase()) {
        case 'arrowdown':
            event.preventDefault();
            navigateSelection(1, fileItems);
            break;
        case 'arrowup':
            event.preventDefault();
            navigateSelection(-1, fileItems);
            break;
        case 'enter':
            event.preventDefault();
            openSelected(fileItems);
            break;
        case 'backspace':
            event.preventDefault();
            goToParent();
            break;
        case '/':
            event.preventDefault();
            const searchBox = document.querySelector('.search-box');
            if (searchBox) {
                searchBox.focus();
                searchBox.select();
            }
            break;
        case 'escape':
            event.preventDefault();
            clearSelection(fileItems);
            break;
        case 'd':
            event.preventDefault();
            downloadSelected(fileItems);
            break;
    }
}

function navigateSelection(direction, fileItems) {
    clearSelection(fileItems);
    currentSelection += direction;
    
    // Wrap around
    if (currentSelection < 0) currentSelection = fileItems.length - 1;
    if (currentSelection >= fileItems.length) currentSelection = 0;
    
    // Highlight selected item
    fileItems[currentSelection].classList.add('selected');
    fileItems[currentSelection].scrollIntoView({ 
        behavior: 'smooth', 
        block: 'nearest' 
    });
}

function clearSelection(fileItems) {
    if (fileItems) {
        fileItems.forEach(item => item.classList.remove('selected'));
    }
    currentSelection = -1;
}

function openSelected(fileItems) {
    if (currentSelection >= 0 && currentSelection < fileItems.length) {
        const selectedItem = fileItems[currentSelection];
        // Check if it's a folder or file
        const onclickAttr = selectedItem.getAttribute('onclick');
        if (onclickAttr && onclickAttr.includes('navigateTo')) {
            selectedItem.click();
        } else {
            // Check file type for appropriate action
            const fileType = selectedItem.getAttribute('data-type');
            const filePath = selectedItem.getAttribute('data-path');
            const fileName = selectedItem.getAttribute('data-name');
            
            if (fileType === 'video') {
                openVideo(filePath, fileName);
            } else {
                previewFile(filePath);
            }
        }
    }
}

function downloadSelected(fileItems) {
    if (currentSelection >= 0 && currentSelection < fileItems.length) {
        const selectedItem = fileItems[currentSelection];
        const downloadButton = selectedItem.querySelector('.btn-download, .btn-secondary');
        if (downloadButton) {
            downloadButton.click();
        }
    }
}

function copySelected(fileItems) {
    if (currentSelection >= 0 && currentSelection < fileItems.length) {
        const selectedItem = fileItems[currentSelection];
        const filePath = selectedItem.getAttribute('data-path');
        const fileName = selectedItem.getAttribute('data-name');
        const fileType = selectedItem.getAttribute('data-type') || 'file';
        
        copyToClipboard(filePath, fileType, fileName);
    }
}

function cutSelected(fileItems) {
    if (currentSelection >= 0 && currentSelection < fileItems.length) {
        const selectedItem = fileItems[currentSelection];
        const filePath = selectedItem.getAttribute('data-path');
        const fileName = selectedItem.getAttribute('data-name');
        const fileType = selectedItem.getAttribute('data-type') || 'file';
        
        cutToClipboard(filePath, fileType, fileName);
    }
}

function navigateTo(path) {
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    window.location.href = '/browse/' + encodedPath;
}

function openFile(path, action) {
    event.stopPropagation();
    
    if (downloadInProgress) {
        alert('Please wait for the current download to complete.');
        return;
    }
    
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    
    switch(action) {
        case 'stream':
            openVideo(path, path.split('/').pop());
            break;
        case 'view':
            window.open('/file/' + encodedPath, '_blank');
            break;
        case 'download':
            window.location.href = '/download/' + encodedPath;
            break;
    }
}

function openVideo(path, filename) {
    event.stopPropagation();
    
    const modal = document.getElementById('videoModal');
    const videoPlayer = document.getElementById('modalVideoPlayer');
    const videoTitle = document.getElementById('videoTitle');
    const videoFileName = document.getElementById('videoFileName');
    
    if (!modal || !videoPlayer) {
        // Fallback: open in new tab
        const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
        window.open('/stream/' + encodedPath, '_blank');
        return;
    }
    
    // Set video info
    videoTitle.textContent = 'Video Player';
    videoFileName.textContent = filename;
    videoPlayer.setAttribute('data-file-path', path);
    
    // Set video source
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    videoPlayer.src = '/stream/' + encodedPath;
    
    // Load playlist
    loadModalPlaylist(path);
    
    // Show modal
    modal.style.display = 'block';
    
    // Load video info
    fetch('/file/' + encodedPath)
        .then(response => {
            if (response.ok) {
                const size = response.headers.get('content-length');
                document.getElementById('videoFileSize').textContent = 
                    formatFileSize(size) || 'Unknown';
            }
        });
    
    // Set up video event listeners
    videoPlayer.addEventListener('loadedmetadata', function() {
        const duration = formatTime(videoPlayer.duration);
        document.getElementById('videoDuration').textContent = duration;
    });
    
    // Attempt to play video
    videoPlayer.load();
    videoPlayer.play().catch(error => {
        console.log('Auto-play prevented:', error);
    });
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    const videoPlayer = document.getElementById('modalVideoPlayer');
    
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    
    if (modal) {
        modal.style.display = 'none';
    }
}

function downloadFolder(path) {
    event.stopPropagation();
    
    if (downloadInProgress) {
        alert('Please wait for the current download to complete.');
        return;
    }
    
    if (!confirm(`Download the entire folder "${path.split('/').pop()}"? This may take a while for large folders.`)) {
        return;
    }
    
    showDownloadProgress(path);
    
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    const downloadLink = document.createElement('a');
    downloadLink.href = '/download_folder/' + encodedPath;
    downloadLink.download = path.split('/').pop() + '.zip';
    
    downloadInProgress = true;
    updateDownloadProgress(0, 'Starting download...');
    
    let progress = 0;
    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += 5;
            updateDownloadProgress(progress, 'Preparing folder...');
        }
    }, 500);
    
    downloadLink.click();
    
    const checkDownload = setInterval(() => {
        const modal = document.getElementById('downloadProgressModal');
        if (!modal || modal.style.display === 'none') {
            clearInterval(progressInterval);
            clearInterval(checkDownload);
            downloadInProgress = false;
            updateDownloadProgress(100, 'Download complete!');
            setTimeout(() => {
                hideDownloadProgress();
            }, 1000);
        }
    }, 1000);
    
    setTimeout(() => {
        if (downloadInProgress) {
            clearInterval(progressInterval);
            clearInterval(checkDownload);
            downloadInProgress = false;
            hideDownloadProgress();
            alert('Download may have completed. Check your downloads folder.');
        }
    }, 300000);
}

function showDownloadProgress(folderPath) {
    const modal = document.getElementById('downloadProgressModal');
    const title = document.getElementById('downloadTitle');
    
    if (modal && title) {
        title.textContent = `Downloading: ${folderPath.split('/').pop()}`;
        modal.style.display = 'block';
        updateDownloadProgress(0, 'Initializing download...');
    }
}

function updateDownloadProgress(percent, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressInfo = document.getElementById('progressInfo');
    
    if (progressFill) {
        progressFill.style.width = percent + '%';
    }
    
    if (progressText) {
        progressText.textContent = message;
    }
    
    if (progressInfo) {
        const now = new Date();
        progressInfo.textContent = `Progress: ${percent}% • ${now.toLocaleTimeString()}`;
    }
}

function hideDownloadProgress() {
    const modal = document.getElementById('downloadProgressModal');
    if (modal) {
        modal.style.display = 'none';
    }
    downloadInProgress = false;
}

function cancelDownload() {
    if (confirm('Cancel the current download?')) {
        hideDownloadProgress();
        downloadInProgress = false;
    }
}

function goToParent() {
    const currentPath = document.body.getAttribute('data-current-path') || '';
    if (currentPath) {
        const pathParts = currentPath.split('/').filter(part => part);
        pathParts.pop();
        const parentPath = pathParts.join('/');
        navigateTo(parentPath);
    }
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatTime(seconds) {
    if (!seconds) return '0:00';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

function initVideoModal() {
    const modal = document.getElementById('videoModal');
    const closeBtn = modal.querySelector('.close');
    
    closeBtn.onclick = closeVideoModal;
    
    window.onclick = function(event) {
        if (event.target == modal) {
            closeVideoModal();
        }
    };
}

function initDownloadModal() {
    const modal = document.getElementById('downloadProgressModal');
    window.onclick = function(event) {
        if (event.target == modal) {
            cancelDownload();
        }
    };
}

function initClipboard() {
    // Load clipboard from localStorage
    const savedClipboard = localStorage.getItem('fileServerClipboard');
    if (savedClipboard) {
        clipboard = JSON.parse(savedClipboard);
        updateClipboardUI();
    }
    
    // Load action history
    const savedHistory = localStorage.getItem('fileServerActionHistory');
    if (savedHistory) {
        actionHistory = JSON.parse(savedHistory);
        updateUndoUI();
    }
}

function saveClipboard() {
    localStorage.setItem('fileServerClipboard', JSON.stringify(clipboard));
    updateClipboardUI();
}

function saveActionHistory() {
    localStorage.setItem('fileServerActionHistory', JSON.stringify(actionHistory));
    updateUndoUI();
}

// Utility function to truncate text
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

// Export functions for HTML onclick
window.navigateTo = navigateTo;
window.openFile = openFile;
window.openVideo = openVideo;
window.downloadFolder = downloadFolder;
window.goToParent = goToParent;
window.cancelDownload = cancelDownload;