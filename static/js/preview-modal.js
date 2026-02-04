// Preview Modal functionality
let currentPreview = {
    filePath: '',
    fileName: '',
    fileType: '',
    fileSize: '',
    mimeType: '',
    prevFile: null,
    nextFile: null,
    totalFiles: 0,
    currentIndex: 0
};

let imageZoom = 1;
let imageRotation = 0;
let showLineNumbers = true;
let wordWrap = false;
let searchResults = [];
let currentSearchIndex = -1;
let currentTextContent = '';

function initPreviewModal() {
    const modal = document.getElementById('previewModal');
    const closeBtn = modal.querySelector('.close');
    
    if (closeBtn) {
        closeBtn.onclick = closePreviewModal;
    }
    
    window.onclick = function(event) {
        if (event.target == modal) {
            closePreviewModal();
        }
        
        const searchModal = document.getElementById('textSearchModal');
        if (event.target == searchModal) {
            closeTextSearchModal();
        }
    };
    
    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const previewModal = document.getElementById('previewModal');
        if (!previewModal || previewModal.style.display !== 'block') return;
        
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                navigateToPrevFile();
                break;
            case 'ArrowRight':
                event.preventDefault();
                navigateToNextFile();
                break;
            case 'Escape':
                event.preventDefault();
                closePreviewModal();
                break;
        }
    });
}

function openPreviewModal(filePath, fileType, event = null) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    console.log('Opening preview for:', filePath, fileType);
    
    const modal = document.getElementById('previewModal');
    if (!modal) {
        console.error('Preview modal not found');
        return;
    }
    
    const loading = document.getElementById('previewLoading');
    
    // Show modal and loading
    modal.style.display = 'block';
    showPreviewSection('previewLoading');
    
    // Reset preview state
    imageZoom = 1;
    imageRotation = 0;
    searchResults = [];
    currentSearchIndex = -1;
    
    // Load preview data
    fetch('/api/preview/' + encodeURIComponent(filePath))
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load preview: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('Preview data received:', data);
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load preview data');
            }
            
            currentPreview = {
                filePath: data.file_path,
                fileName: data.filename,
                fileType: data.file_type,
                fileSize: data.file_size,
                mimeType: data.mime_type,
                prevFile: data.prev_file,
                nextFile: data.next_file,
                totalFiles: data.total_files,
                currentIndex: data.current_index
            };
            
            updatePreviewUI();
            
            // Load content based on file type
            switch(data.file_type) {
                case 'image':
                    loadImagePreview();
                    break;
                case 'text':
                    loadTextPreview();
                    break;
                case 'document':
                    loadDocumentPreview();
                    break;
                case 'video':
                case 'audio':
                    showMediaPreview();
                    break;
                default:
                    showGenericPreview();
                    break;
            }
        })
        .catch(error => {
            console.error('Error loading preview:', error);
            alert('Error loading preview: ' + error.message);
            closePreviewModal();
        });
}

function closePreviewModal() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    // Reset states
    imageZoom = 1;
    imageRotation = 0;
    searchResults = [];
    currentSearchIndex = -1;
    currentTextContent = '';
}

function showPreviewSection(sectionId) {
    console.log('Showing section:', sectionId);
    // Hide all sections
    const sections = document.querySelectorAll('.preview-section');
    if (sections) {
        sections.forEach(section => {
            if (section) section.style.display = 'none';
        });
    }
    
    // Show requested section
    const section = document.getElementById(sectionId);
    if (section) {
        section.style.display = 'block';
    }
}

function updatePreviewUI() {
    console.log('Updating UI with:', currentPreview);
    
    // Update file info
    const updateElement = (id, text) => {
        const element = document.getElementById(id);
        if (element) element.textContent = text || '-';
    };
    
    updateElement('previewFileName', currentPreview.fileName);
    updateElement('previewFileSize', currentPreview.fileSize);
    updateElement('previewFileType', currentPreview.fileType ? 
        currentPreview.fileType.charAt(0).toUpperCase() + currentPreview.fileType.slice(1) : '');
    
    if (currentPreview.totalFiles > 1) {
        updateElement('previewFilePosition', `File ${currentPreview.currentIndex} of ${currentPreview.totalFiles}`);
    } else {
        updateElement('previewFilePosition', '');
    }
    
    updateElement('previewFilePath', currentPreview.filePath);
    updateElement('previewFileMime', currentPreview.mimeType);
    
    // Update file icon
    const icon = document.getElementById('previewFileIcon');
    if (icon) {
        switch(currentPreview.fileType) {
            case 'image': icon.textContent = '🖼️'; break;
            case 'text': icon.textContent = '📝'; break;
            case 'document': icon.textContent = '📄'; break;
            case 'video': icon.textContent = '🎬'; break;
            case 'audio': icon.textContent = '🎵'; break;
            default: icon.textContent = '📄'; break;
        }
    }
    
    // Update navigation buttons
    const prevBtn = document.getElementById('prevFileBtn');
    const nextBtn = document.getElementById('nextFileBtn');
    if (prevBtn) prevBtn.disabled = !currentPreview.prevFile;
    if (nextBtn) nextBtn.disabled = !currentPreview.nextFile;
}

function loadImagePreview() {
    console.log('Loading image preview for:', currentPreview.filePath);
    showPreviewSection('imagePreview');
    
    const img = document.getElementById('previewImage');
    if (!img) {
        showGenericPreview();
        return;
    }
    
    const encodedPath = encodeURIComponent(currentPreview.filePath);
    img.src = '/file/' + encodedPath;
    img.style.transform = `scale(${imageZoom}) rotate(${imageRotation}deg)`;
    img.alt = currentPreview.fileName;
    
    img.onload = function() {
        console.log('Image loaded successfully');
        img.addEventListener('wheel', function(e) {
            e.preventDefault();
            zoomPreviewImage(e.deltaY > 0 ? 0.9 : 1.1);
        });
    };
    
    img.onerror = function() {
        console.error('Failed to load image:', img.src);
        img.src = ''; // Clear broken image
        showGenericPreview();
    };
}

function loadTextPreview() {
    console.log('Loading text preview for:', currentPreview.filePath);
    showPreviewSection('textPreview');
    
    fetch('/api/file_content/' + encodeURIComponent(currentPreview.filePath))
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load file content: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Failed to load content');
            }
            
            currentTextContent = data.content || '';
            updateTextPreview();
        })
        .catch(error => {
            console.error('Error loading text content:', error);
            const preview = document.getElementById('previewTextContent');
            if (preview) {
                preview.textContent = 'Error loading file content: ' + error.message;
            }
        });
}

function updateTextPreview() {
    const preview = document.getElementById('previewTextContent');
    if (!preview) return;
    
    let text = currentTextContent || '';
    
    if (showLineNumbers) {
        text = addLineNumbers(text);
    }
    
    preview.textContent = text;
    preview.className = `text-content theme-dark`;
    applyTextSettings();
}

function addLineNumbers(text) {
    const lines = text.split('\n');
    const maxLineNum = lines.length.toString().length;
    
    return lines.map((line, index) => {
        const lineNum = (index + 1).toString().padStart(maxLineNum, ' ');
        return `${lineNum} | ${line}`;
    }).join('\n');
}

function loadDocumentPreview() {
    console.log('Loading document preview for:', currentPreview.filePath);
    showPreviewSection('documentPreview');
    
    // Update document info
    const updateElement = (id, text) => {
        const element = document.getElementById(id);
        if (element) element.textContent = text;
    };
    
    updateElement('documentFileName', currentPreview.fileName);
    updateElement('documentFileInfo', `${currentPreview.fileSize} • ${currentPreview.mimeType}`);
    
    // Check document type
    const fileName = currentPreview.fileName.toLowerCase();
    const pdfPreview = document.getElementById('pdfPreview');
    const wordPreview = document.getElementById('wordPreview');
    const docInfo = document.querySelector('.document-info p');
    
    // Handle PDF files
    if (fileName.endsWith('.pdf') && pdfPreview) {
        pdfPreview.style.display = 'block';
        if (wordPreview) wordPreview.style.display = 'none';
        const encodedPath = encodeURIComponent(currentPreview.filePath);
        const pdfFrame = document.getElementById('pdfFrame');
        if (pdfFrame) {
            pdfFrame.src = '/file/' + encodedPath + '#toolbar=0&navpanes=0';
        }
        if (docInfo) {
            docInfo.textContent = 'PDF document preview. You can also download the file.';
        }
    } 
    // Handle Word documents
    else if (fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
        if (pdfPreview) pdfPreview.style.display = 'none';
        if (wordPreview) {
            wordPreview.style.display = 'block';
            loadWordDocumentPreview();
        }
        if (docInfo) {
            docInfo.innerHTML = `
                Word document preview. The document has been converted to HTML for viewing.<br>
                Formatting may not be perfect. For the best experience, download the original file.
            `;
        }
        
        // Update buttons for Word documents
        const docActions = document.querySelector('.document-actions');
        if (docActions) {
            docActions.innerHTML = `
                <button class="btn btn-primary" onclick="downloadCurrentPreview()">⬇️ Download Original</button>
                <button class="btn btn-secondary" onclick="openInWordOnline()">Open in Word Online</button>
            `;
        }
    } 
    // Handle Excel documents
    else if (fileName.endsWith('.xls') || fileName.endsWith('.xlsx')) {
        if (pdfPreview) pdfPreview.style.display = 'none';
        if (wordPreview) wordPreview.style.display = 'none';
        if (docInfo) {
            docInfo.innerHTML = `
                Excel documents cannot be previewed directly in the browser.<br>
                You can:<br>
                1. Download and open with Microsoft Excel<br>
                2. Open in Google Sheets (if uploaded to Google Drive)
            `;
        }
    }
    // Handle PowerPoint documents
    else if (fileName.endsWith('.ppt') || fileName.endsWith('.pptx')) {
        if (pdfPreview) pdfPreview.style.display = 'none';
        if (wordPreview) wordPreview.style.display = 'none';
        if (docInfo) {
            docInfo.innerHTML = `
                PowerPoint documents cannot be previewed directly in the browser.<br>
                You can:<br>
                1. Download and open with Microsoft PowerPoint<br>
                2. Open in Google Slides (if uploaded to Google Drive)
            `;
        }
    }
    // Other documents
    else {
        if (pdfPreview) pdfPreview.style.display = 'none';
        if (wordPreview) wordPreview.style.display = 'none';
        if (docInfo) {
            docInfo.textContent = 'This document cannot be previewed inline. Please open in browser or download.';
        }
    }
}

function loadWordDocumentPreview() {
    console.log('Loading Word document preview for:', currentPreview.filePath);
    
    const wordPreviewContent = document.getElementById('wordPreviewContent');
    if (!wordPreviewContent) {
        console.error('Word preview content element not found');
        return;
    }
    
    // Show loading message
    wordPreviewContent.innerHTML = '<div class="loading-spinner"></div><p>Converting Word document to HTML...</p>';
    
    // Fetch converted Word document content
    fetch('/api/word_document_content/' + encodeURIComponent(currentPreview.filePath))
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load Word document: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Failed to convert Word document');
            }
            
            // Display the converted HTML
            wordPreviewContent.innerHTML = data.content || '<p>No content available.</p>';
            
            // Add Word document specific controls
            const wordControls = document.createElement('div');
            wordControls.className = 'word-document-controls';
            wordControls.innerHTML = `
                <div class="word-controls-panel">
                    <span>Word Document Controls:</span>
                    <button class="btn-control" onclick="zoomWordDocument(1.2)">+ Zoom</button>
                    <button class="btn-control" onclick="zoomWordDocument(0.8)">- Zoom</button>
                    <button class="btn-control" onclick="toggleWordDocumentTheme()">Toggle Theme</button>
                    <button class="btn-control" onclick="printWordDocument()">Print</button>
                </div>
            `;
            
            // Insert controls at the beginning
            wordPreviewContent.insertBefore(wordControls, wordPreviewContent.firstChild);
            
            // Add event listeners for Word document scrolling
            const wordDoc = wordPreviewContent.querySelector('.word-document-preview');
            if (wordDoc) {
                wordDoc.addEventListener('scroll', function() {
                    updateWordDocumentScrollPosition();
                });
            }
            
        })
        .catch(error => {
            console.error('Error loading Word document:', error);
            wordPreviewContent.innerHTML = `
                <div class="error-message">
                    <p>Error loading Word document: ${error.message}</p>
                    <p>Please download the file to view it properly.</p>
                    <button class="btn btn-primary" onclick="downloadCurrentPreview()">Download File</button>
                </div>
            `;
        });
}

function zoomWordDocument(factor) {
    const wordPreview = document.getElementById('wordPreviewContent');
    if (!wordPreview) return;
    
    const wordDoc = wordPreview.querySelector('.word-document-preview');
    if (!wordDoc) return;
    
    const currentZoom = parseFloat(wordDoc.style.zoom) || 1;
    const newZoom = currentZoom * factor;
    
    // Limit zoom between 0.5 and 3
    if (newZoom >= 0.5 && newZoom <= 3) {
        wordDoc.style.zoom = newZoom;
    }
}

function toggleWordDocumentTheme() {
    const wordPreview = document.getElementById('wordPreviewContent');
    if (!wordPreview) return;
    
    const wordDoc = wordPreview.querySelector('.word-document-preview');
    if (!wordDoc) return;
    
    if (wordDoc.classList.contains('dark-theme')) {
        wordDoc.classList.remove('dark-theme');
        wordDoc.classList.add('light-theme');
    } else {
        wordDoc.classList.remove('light-theme');
        wordDoc.classList.add('dark-theme');
    }
}

function printWordDocument() {
    const wordPreview = document.getElementById('wordPreviewContent');
    if (!wordPreview) return;
    
    const printContent = wordPreview.innerHTML;
    const originalContent = document.body.innerHTML;
    
    document.body.innerHTML = printContent;
    window.print();
    document.body.innerHTML = originalContent;
    window.location.reload();
}

function updateWordDocumentScrollPosition() {
    // Could be used to show scroll position or sync with outline
}

function openInWordOnline() {
    // This would require integration with Microsoft Graph API
    // For now, just open the file in browser
    const encodedPath = encodeURIComponent(currentPreview.filePath);
    window.open('/file/' + encodedPath, '_blank');
}

function showMediaPreview() {
    console.log('Showing media preview for:', currentPreview.filePath);
    showPreviewSection('genericPreview');
    
    const typeName = currentPreview.fileType === 'video' ? 'Video' : 'Audio';
    const message = currentPreview.fileType === 'video' 
        ? 'Video files cannot be previewed. Use the Stream button to play videos.'
        : 'Audio files cannot be previewed. Use the Stream button to play audio.';
    
    // Update generic preview content
    const genericIcon = document.querySelector('#genericPreview .generic-icon');
    const genericFileName = document.getElementById('genericFileName');
    const genericFileInfo = document.getElementById('genericFileInfo');
    const genericActions = document.querySelector('#genericPreview .generic-actions');
    
    if (genericIcon) genericIcon.textContent = currentPreview.fileType === 'video' ? '🎬' : '🎵';
    if (genericFileName) genericFileName.textContent = currentPreview.fileName;
    if (genericFileInfo) genericFileInfo.textContent = `${currentPreview.fileSize} • ${typeName} • ${currentPreview.mimeType}`;
    
    // Update the message in the generic preview
    const messageElement = document.querySelector('#genericPreview p');
    if (messageElement) messageElement.textContent = message;
    
    // Update buttons
    if (genericActions) {
        genericActions.innerHTML = `
            <button class="btn btn-primary" onclick="${currentPreview.fileType === 'video' ? 'openVideoModal' : 'openAudioModal'}('${currentPreview.filePath}', '${currentPreview.fileName}', event)">Stream</button>
            <button class="btn btn-secondary" onclick="downloadCurrentPreview()">Download</button>
        `;
    }
}

function showGenericPreview() {
    console.log('Showing generic preview for:', currentPreview.filePath);
    showPreviewSection('genericPreview');
    
    const genericFileName = document.getElementById('genericFileName');
    const genericFileInfo = document.getElementById('genericFileInfo');
    
    if (genericFileName) genericFileName.textContent = currentPreview.fileName;
    if (genericFileInfo) genericFileInfo.textContent = `${currentPreview.fileSize} • ${currentPreview.fileType} • ${currentPreview.mimeType}`;
}

function navigateToPrevFile() {
    if (currentPreview.prevFile) {
        console.log('Navigating to previous file:', currentPreview.prevFile);
        openPreviewModal(currentPreview.prevFile.path, currentPreview.prevFile.type);
    }
}

function navigateToNextFile() {
    if (currentPreview.nextFile) {
        console.log('Navigating to next file:', currentPreview.nextFile);
        openPreviewModal(currentPreview.nextFile.path, currentPreview.nextFile.type);
    }
}

function downloadCurrentPreview() {
    window.location.href = '/download/' + encodeURIComponent(currentPreview.filePath);
}

function deleteCurrentPreview() {
    if (confirm(`Are you sure you want to delete "${currentPreview.fileName}"?`)) {
        fetch('/delete/' + encodeURIComponent(currentPreview.filePath), {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('File deleted successfully');
                closePreviewModal();
                window.location.reload(); // Refresh to update file list
            } else {
                alert('Error deleting file: ' + data.error);
            }
        })
        .catch(error => {
            alert('Error deleting file');
        });
    }
}

function openPreviewInBrowser() {
    window.open('/file/' + encodeURIComponent(currentPreview.filePath), '_blank');
}

// Image controls
function zoomPreviewImage(factor) {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageZoom *= factor;
    if (imageZoom > 5) imageZoom = 5;
    if (imageZoom < 0.1) imageZoom = 0.1;
    
    img.style.transform = `scale(${imageZoom}) rotate(${imageRotation}deg)`;
}

function rotatePreviewImage() {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageRotation += 90;
    img.style.transform = `scale(${imageZoom}) rotate(${imageRotation}deg)`;
}

function resetPreviewImage() {
    const img = document.getElementById('previewImage');
    if (!img) return;
    
    imageZoom = 1;
    imageRotation = 0;
    img.style.transform = 'scale(1) rotate(0deg)';
}

// Text controls
function changePreviewFontSize(size) {
    const preview = document.getElementById('previewTextContent');
    if (preview) preview.style.fontSize = size + 'px';
}

function changePreviewTheme(theme) {
    const preview = document.getElementById('previewTextContent');
    if (preview) preview.className = `text-content theme-${theme}`;
}

function togglePreviewLineNumbers() {
    showLineNumbers = !showLineNumbers;
    updateTextPreview();
}

function togglePreviewWordWrap() {
    const preview = document.getElementById('previewTextContent');
    if (preview) {
        wordWrap = !wordWrap;
        preview.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
    }
}

function applyTextSettings() {
    const preview = document.getElementById('previewTextContent');
    if (preview) {
        preview.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
    }
}

// Text search functions
function searchInPreviewText() {
    const modal = document.getElementById('textSearchModal');
    if (modal) {
        modal.style.display = 'block';
        setTimeout(() => {
            const searchText = document.getElementById('searchText');
            if (searchText) searchText.focus();
        }, 100);
    }
}

function closeTextSearchModal() {
    const modal = document.getElementById('textSearchModal');
    if (modal) modal.style.display = 'none';
    clearSearchHighlights();
}

function performTextSearch() {
    const searchInput = document.getElementById('searchText');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value;
    if (!searchTerm) {
        alert('Please enter a search term');
        return;
    }
    
    const caseSensitive = document.getElementById('caseSensitive')?.checked || false;
    const wholeWord = document.getElementById('wholeWord')?.checked || false;
    
    const preview = document.getElementById('previewTextContent');
    if (!preview) return;
    
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
    const preview = document.getElementById('previewTextContent');
    if (!preview) return;
    
    // Remove all highlight spans
    preview.innerHTML = preview.innerHTML
        .replace(/<span class="highlight">/g, '')
        .replace(/<span class="current-highlight">/g, '')
        .replace(/<\/span>/g, '');
    
    searchResults = [];
    currentSearchIndex = -1;
}

function highlightSearchResults() {
    const preview = document.getElementById('previewTextContent');
    if (!preview) return;
    
    let html = preview.textContent;
    
    // Highlight all matches (backwards to preserve indices)
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
    
    const preview = document.getElementById('previewTextContent');
    if (!preview) return;
    
    const result = searchResults[currentSearchIndex];
    
    // Scroll to the result
    const lineHeight = 20;
    const text = preview.textContent;
    const linesBefore = text.substring(0, result.index).split('\n').length;
    preview.scrollTop = (linesBefore - 5) * lineHeight;
    
    // Update highlights
    highlightSearchResults();
    
    // Show current position
    alert(`Found ${searchResults.length} matches. Current: ${currentSearchIndex + 1}/${searchResults.length}`);
}

// Export functions for global use
window.openPreviewModal = openPreviewModal;
window.closePreviewModal = closePreviewModal;
window.navigateToPrevFile = navigateToPrevFile;
window.navigateToNextFile = navigateToNextFile;
window.downloadCurrentPreview = downloadCurrentPreview;
window.deleteCurrentPreview = deleteCurrentPreview;
window.openPreviewInBrowser = openPreviewInBrowser;
window.zoomPreviewImage = zoomPreviewImage;
window.rotatePreviewImage = rotatePreviewImage;
window.resetPreviewImage = resetPreviewImage;
window.changePreviewFontSize = changePreviewFontSize;
window.changePreviewTheme = changePreviewTheme;
window.togglePreviewLineNumbers = togglePreviewLineNumbers;
window.togglePreviewWordWrap = togglePreviewWordWrap;
window.searchInPreviewText = searchInPreviewText;
window.closeTextSearchModal = closeTextSearchModal;
window.performTextSearch = performTextSearch;
window.loadWordDocumentPreview = loadWordDocumentPreview;
window.zoomWordDocument = zoomWordDocument;
window.toggleWordDocumentTheme = toggleWordDocumentTheme;
window.printWordDocument = printWordDocument;
window.openInWordOnline = openInWordOnline;