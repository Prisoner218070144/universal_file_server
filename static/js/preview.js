// Preview page functionality - No video support
let currentFile = {
    path: document.body.getAttribute('data-file-path') || '',
    type: document.body.getAttribute('data-file-type') || '',
    name: document.body.getAttribute('data-file-name') || ''
};

// Image preview variables
let imageZoom = 1;
let imageRotation = 0;

// Text preview variables
let showLineNumbers = true;
let wordWrap = false;
let searchResults = [];
let currentSearchIndex = -1;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load file content based on type
    if (currentFile.type === 'text') {
        loadTextFile();
    } else if (currentFile.type === 'image') {
        initImagePreview();
    }
    
    // Set up keyboard shortcuts
    setupKeyboardShortcuts();
});

function goBack() {
    const dirPath = currentFile.path.substring(0, currentFile.path.lastIndexOf('/'));
    window.location.href = '/browse/' + encodeURIComponent(dirPath);
}

function downloadFile(filePath) {
    window.location.href = '/download/' + encodeURIComponent(filePath);
}

function openInBrowser(filePath) {
    window.open('/file/' + encodeURIComponent(filePath), '_blank');
}

function deleteFile(filePath) {
    document.getElementById('deleteFileName').textContent = currentFile.name;
    document.getElementById('deleteModal').style.display = 'block';
    window.deleteFilePath = filePath;
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    window.deleteFilePath = null;
}

function confirmDelete() {
    if (!window.deleteFilePath) return;
    
    fetch('/delete/' + encodeURIComponent(window.deleteFilePath), {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('File deleted successfully');
            goBack();
        } else {
            alert('Error deleting file: ' + data.error);
        }
        closeDeleteModal();
    })
    .catch(error => {
        alert('Error deleting file');
        closeDeleteModal();
    });
}

// Image preview functions
function zoomImage(factor) {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageZoom *= factor;
    img.style.transform = `scale(${imageZoom}) rotate(${imageRotation}deg)`;
    
    // Limit zoom
    if (imageZoom > 5) imageZoom = 5;
    if (imageZoom < 0.1) imageZoom = 0.1;
}

function rotateImage() {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageRotation += 90;
    img.style.transform = `scale(${imageZoom}) rotate(${imageRotation}deg)`;
}

function resetImage() {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageZoom = 1;
    imageRotation = 0;
    img.style.transform = 'scale(1) rotate(0deg)';
}

function initImagePreview() {
    const img = document.getElementById('previewImage');
    if (img) {
        img.onload = function() {
            // Add zoom controls
            img.addEventListener('wheel', function(e) {
                e.preventDefault();
                zoomImage(e.deltaY > 0 ? 0.9 : 1.1);
            });
        };
    }
}

// Text preview functions
function loadTextFile() {
    fetch('/file/' + encodeURIComponent(currentFile.path))
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load file');
            }
            return response.text();
        })
        .then(text => {
            const preview = document.getElementById('textPreview');
            if (showLineNumbers) {
                text = addLineNumbers(text);
            }
            preview.textContent = text;
            preview.className = `text-preview theme-dark`;
            applyTextSettings();
        })
        .catch(error => {
            document.getElementById('textPreview').textContent = 'Error loading file content: ' + error.message;
        });
}

function addLineNumbers(text) {
    const lines = text.split('\n');
    const maxLineNum = lines.length.toString().length;
    
    return lines.map((line, index) => {
        const lineNum = (index + 1).toString().padStart(maxLineNum, ' ');
        return `${lineNum} | ${line}`;
    }).join('\n');
}

function changeFontSize(size) {
    const preview = document.getElementById('textPreview');
    preview.style.fontSize = size + 'px';
}

function changeTheme(theme) {
    const preview = document.getElementById('textPreview');
    preview.className = `text-preview theme-${theme}`;
}

function toggleLineNumbers() {
    showLineNumbers = !showLineNumbers;
    loadTextFile();
}

function toggleWordWrap() {
    const preview = document.getElementById('textPreview');
    wordWrap = !wordWrap;
    preview.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
}

function applyTextSettings() {
    const preview = document.getElementById('textPreview');
    preview.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
}

function searchInText() {
    document.getElementById('textSearchModal').style.display = 'block';
    setTimeout(() => {
        document.getElementById('searchText').focus();
    }, 100);
}

function closeTextSearchModal() {
    document.getElementById('textSearchModal').style.display = 'none';
    clearSearchHighlights();
}

function performTextSearch() {
    const searchTerm = document.getElementById('searchText').value;
    const caseSensitive = document.getElementById('caseSensitive').checked;
    const wholeWord = document.getElementById('wholeWord').checked;
    
    if (!searchTerm) {
        alert('Please enter a search term');
        return;
    }
    
    const preview = document.getElementById('textPreview');
    let text = preview.textContent;
    
    // Clear previous highlights
    clearSearchHighlights();
    
    // Build regex pattern
    let pattern = searchTerm;
    if (wholeWord) {
        pattern = `\\b${pattern}\\b`;
    }
    
    const flags = caseSensitive ? 'g' : 'gi';
    const regex = new RegExp(pattern, flags);
    
    // Find all matches
    searchResults = [];
    let match;
    while ((match = regex.exec(text)) !== null) {
        searchResults.push({
            index: match.index,
            length: match[0].length
        });
    }
    
    if (searchResults.length === 0) {
        alert('No matches found');
        return;
    }
    
    // Highlight matches
    highlightSearchResults();
    navigateToSearchResult(0);
    
    closeTextSearchModal();
}

function clearSearchHighlights() {
    const preview = document.getElementById('textPreview');
    preview.innerHTML = preview.innerHTML
        .replace(/<span class="highlight">/g, '')
        .replace(/<span class="current-highlight">/g, '')
        .replace(/<\/span>/g, '');
    
    searchResults = [];
    currentSearchIndex = -1;
}

function highlightSearchResults() {
    const preview = document.getElementById('textPreview');
    let html = preview.textContent;
    
    // Highlight all matches
    for (let i = searchResults.length - 1; i >= 0; i--) {
        const result = searchResults[i];
        const before = html.substring(0, result.index);
        const match = html.substring(result.index, result.index + result.length);
        const after = html.substring(result.index + result.length);
        
        const highlightClass = i === currentSearchIndex ? 'current-highlight' : 'highlight';
        html = before + `<span class="${highlightClass}">${match}</span>` + after;
    }
    
    preview.innerHTML = html;
}

function navigateToSearchResult(index) {
    if (searchResults.length === 0) return;
    
    currentSearchIndex = index;
    if (currentSearchIndex >= searchResults.length) {
        currentSearchIndex = 0;
    }
    if (currentSearchIndex < 0) {
        currentSearchIndex = searchResults.length - 1;
    }
    
    // Scroll to the result
    const preview = document.getElementById('textPreview');
    const result = searchResults[currentSearchIndex];
    
    // Create a temporary span to measure position
    const tempSpan = document.createElement('span');
    tempSpan.id = 'temp-highlight';
    preview.appendChild(tempSpan);
    
    // Scroll to position
    preview.scrollTop = (result.index / text.length) * preview.scrollHeight;
    
    // Update highlights
    highlightSearchResults();
    
    // Show current position
    alert(`Found ${searchResults.length} matches. Current: ${currentSearchIndex + 1}/${searchResults.length}`);
}

// Navigation functions
function navigateToPrev() {
    const prevPath = document.body.getAttribute('data-prev-path');
    if (prevPath) {
        window.location.href = '/preview/' + encodeURIComponent(prevPath);
    }
}

function navigateToNext() {
    const nextPath = document.body.getAttribute('data-next-path');
    if (nextPath) {
        window.location.href = '/preview/' + encodeURIComponent(nextPath);
    }
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Don't trigger shortcuts when typing in inputs
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
            return;
        }
        
        // Handle search navigation
        if (event.ctrlKey || event.metaKey) {
            switch(event.key.toLowerCase()) {
                case 'f':
                    event.preventDefault();
                    searchInText();
                    break;
                case 'g':
                    if (searchResults.length > 0) {
                        event.preventDefault();
                        navigateToSearchResult(currentSearchIndex + 1);
                    }
                    break;
            }
            return;
        }
        
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                navigateToPrev();
                break;
            case 'ArrowRight':
                event.preventDefault();
                navigateToNext();
                break;
            case 'Escape':
                event.preventDefault();
                if (document.getElementById('deleteModal').style.display === 'block') {
                    closeDeleteModal();
                } else if (document.getElementById('textSearchModal').style.display === 'block') {
                    closeTextSearchModal();
                } else {
                    goBack();
                }
                break;
            case 'd':
            case 'D':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    downloadFile(currentFile.path);
                }
                break;
        }
    });
}

// Close modals when clicking outside
window.onclick = function(event) {
    const deleteModal = document.getElementById('deleteModal');
    if (event.target == deleteModal) {
        closeDeleteModal();
    }
    
    const searchModal = document.getElementById('textSearchModal');
    if (event.target == searchModal) {
        closeTextSearchModal();
    }
};

// Export functions for HTML onclick
window.goBack = goBack;
window.downloadFile = downloadFile;
window.openInBrowser = openInBrowser;
window.deleteFile = deleteFile;
window.closeDeleteModal = closeDeleteModal;
window.confirmDelete = confirmDelete;
window.zoomImage = zoomImage;
window.rotateImage = rotateImage;
window.resetImage = resetImage;
window.changeFontSize = changeFontSize;
window.changeTheme = changeTheme;
window.toggleLineNumbers = toggleLineNumbers;
window.toggleWordWrap = toggleWordWrap;
window.searchInText = searchInText;
window.closeTextSearchModal = closeTextSearchModal;
window.performTextSearch = performTextSearch;
window.navigateToPrev = navigateToPrev;
window.navigateToNext = navigateToNext;