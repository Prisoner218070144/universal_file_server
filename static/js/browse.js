// Browse page functionality
let selectedFiles = [];
let isUploading = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initUploadHandlers();
    initKeyboardShortcuts();
    initModalCloseButtons();
});

function initModalCloseButtons() {
    // Get all close buttons
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(btn => {
        btn.onclick = function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        };
    });
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
            
            // Reset forms if needed
            if (event.target.id === 'uploadModal') {
                resetUploadForm();
            } else if (event.target.id === 'createFolderModal') {
                document.getElementById('folderName').value = '';
            } else if (event.target.id === 'createFileModal') {
                document.getElementById('fileName').value = '';
            } else if (event.target.id === 'moveCopyModal') {
                // Don't reset move/copy modal
            }
        }
    };
}

function initUploadHandlers() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    if (!dropZone || !fileInput) return;
    
    // Click to browse
    dropZone.addEventListener('click', (e) => {
        if (e.target !== dropZone && !e.target.classList.contains('btn-browse')) {
            return;
        }
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
        dropZone.style.borderColor = '#4CAF50';
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
        dropZone.style.borderColor = '#444';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
        dropZone.style.borderColor = '#444';
        
        if (e.dataTransfer.files.length) {
            handleFiles(e.dataTransfer.files);
        }
    });
}

function handleFiles(files) {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;
    
    fileList.innerHTML = '';
    selectedFiles = Array.from(files);
    
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '<div class="no-files">No files selected</div>';
        updateUploadButton();
        return;
    }
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item-upload';
        fileItem.innerHTML = `
            <span title="${file.name}">${truncateText(file.name, 30)}</span>
            <span>${formatFileSize(file.size)}</span>
        `;
        fileList.appendChild(fileItem);
    });
    
    updateUploadButton();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

function updateUploadButton() {
    const uploadButton = document.getElementById('uploadButton');
    if (!uploadButton) return;
    
    if (selectedFiles.length === 0) {
        uploadButton.disabled = true;
        uploadButton.textContent = 'Upload Files';
        uploadButton.style.opacity = '0.5';
    } else {
        uploadButton.disabled = false;
        uploadButton.textContent = `Upload ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}`;
        uploadButton.style.opacity = '1';
    }
}

function startUpload() {
    if (isUploading || selectedFiles.length === 0) return;
    
    const currentPath = document.body.getAttribute('data-current-path') || '';
    const formData = new FormData();
    
    selectedFiles.forEach(file => {
        formData.append('files[]', file);
    });
    
    isUploading = true;
    updateUploadProgress(0, 'Starting upload...');
    
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            updateUploadProgress(percentComplete, `Uploading... ${Math.round(percentComplete)}%`);
        }
    });
    
    xhr.addEventListener('load', () => {
        try {
            const response = JSON.parse(xhr.responseText);
            if (xhr.status === 200) {
                if (response.success && response.success.length > 0) {
                    updateUploadProgress(100, 'Upload complete!');
                    setTimeout(() => {
                        alert(`${response.success.length} file${response.success.length > 1 ? 's' : ''} uploaded successfully`);
                        window.location.reload();
                    }, 1000);
                } else {
                    updateUploadProgress(0, 'Upload failed');
                    if (response.error) {
                        alert('Upload failed: ' + response.error);
                    } else if (response.errors && response.errors.length > 0) {
                        alert('Some files failed to upload');
                    } else {
                        alert('Upload failed: Unknown error');
                    }
                }
            } else {
                updateUploadProgress(0, 'Upload failed');
                alert('Upload failed: ' + (response.error || 'Server error'));
            }
        } catch (e) {
            updateUploadProgress(0, 'Upload failed');
            alert('Error parsing server response');
        }
        isUploading = false;
    });
    
    xhr.addEventListener('error', () => {
        updateUploadProgress(0, 'Upload failed');
        alert('Network error during upload');
        isUploading = false;
    });
    
    let url = '/upload/';
    if (currentPath) {
        url = '/upload/' + encodeURIComponent(currentPath);
    }
    
    xhr.open('POST', url);
    xhr.send(formData);
}

function updateUploadProgress(percent, message) {
    const progressFill = document.getElementById('uploadProgressFill');
    const progressText = document.getElementById('uploadProgressText');
    
    if (progressFill) {
        progressFill.style.width = percent + '%';
    }
    
    if (progressText) {
        progressText.textContent = message;
    }
}

function resetUploadForm() {
    selectedFiles = [];
    isUploading = false;
    
    const fileList = document.getElementById('fileList');
    const fileInput = document.getElementById('fileInput');
    
    if (fileList) fileList.innerHTML = '<div class="no-files">No files selected</div>';
    if (fileInput) fileInput.value = '';
    
    updateUploadProgress(0, 'Ready to upload');
    updateUploadButton();
}

function createFolder() {
    const folderNameInput = document.getElementById('folderName');
    if (!folderNameInput) return;
    
    const folderName = folderNameInput.value.trim();
    if (!folderName) {
        alert('Please enter a folder name');
        folderNameInput.focus();
        return;
    }
    
    const currentPath = document.body.getAttribute('data-current-path') || '';
    
    let url = '/create_folder/';
    if (currentPath) {
        url = '/create_folder/' + encodeURIComponent(currentPath);
    }
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ folder_name: folderName })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`Folder "${folderName}" created successfully`);
            closeCreateFolderModal();
            window.location.reload();
        } else {
            alert(`Error creating folder: ${data.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        alert('Error creating folder: ' + error.message);
    });
}

function createFile() {
    const fileNameInput = document.getElementById('fileName');
    if (!fileNameInput) return;
    
    const fileName = fileNameInput.value.trim();
    if (!fileName) {
        alert('Please enter a file name');
        fileNameInput.focus();
        return;
    }
    
    const currentPath = document.body.getAttribute('data-current-path') || '';
    
    let url = '/create_file/';
    if (currentPath) {
        url = '/create_file/' + encodeURIComponent(currentPath);
    }
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename: fileName })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`File "${fileName}" created successfully`);
            closeCreateFileModal();
            window.location.reload();
        } else {
            alert(`Error creating file: ${data.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        alert('Error creating file: ' + error.message);
    });
}

function previewFile(filePath) {
    window.location.href = '/preview/' + encodeURIComponent(filePath);
}

function downloadFile(filePath) {
    event.stopPropagation();
    window.location.href = '/download/' + encodeURIComponent(filePath);
}

function navigateTo(path) {
    const encodedPath = encodeURIComponent(path);
    if (path === '' || path === '/') {
        window.location.href = '/browse/';
    } else {
        window.location.href = '/browse/' + encodedPath;
    }
}

function downloadFolder(path) {
    event.stopPropagation();
    
    if (!confirm(`Download the entire folder "${path.split('/').pop() || 'F Drive'}"? This may take a while for large folders.`)) {
        return;
    }
    
    const encodedPath = encodeURIComponent(path);
    window.location.href = '/download_folder/' + encodedPath;
}

function deleteItem(itemPath, type) {
    event.stopPropagation();
    
    const itemName = itemPath.split('/').pop();
    document.getElementById('deleteItemName').textContent = itemName;
    document.getElementById('deleteWarning').textContent = 
        type === 'folder' ? 'This will delete the folder and all its contents.' : 'This action cannot be undone.';
    document.getElementById('deleteModal').style.display = 'block';
    window.deleteItemPath = itemPath;
    window.deleteItemType = type;
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    window.deleteItemPath = null;
    window.deleteItemType = null;
}

function confirmDelete() {
    if (!window.deleteItemPath) return;
    
    fetch('/delete/' + encodeURIComponent(window.deleteItemPath), {
        method: 'DELETE',
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`${window.deleteItemType} deleted successfully`);
            window.location.reload();
        } else {
            alert('Error deleting: ' + data.error);
        }
        closeDeleteModal();
    })
    .catch(error => {
        alert('Error deleting');
        closeDeleteModal();
    });
}

// Modal display functions
function showUploadModal() {
    document.getElementById('uploadModal').style.display = 'block';
}

function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
    resetUploadForm();
}

function showCreateFolderModal() {
    document.getElementById('createFolderModal').style.display = 'block';
    setTimeout(() => {
        document.getElementById('folderName').focus();
    }, 100);
}

function closeCreateFolderModal() {
    document.getElementById('createFolderModal').style.display = 'none';
    document.getElementById('folderName').value = '';
}

function showCreateFileModal() {
    document.getElementById('createFileModal').style.display = 'block';
    setTimeout(() => {
        document.getElementById('fileName').focus();
    }, 100);
}

function closeCreateFileModal() {
    document.getElementById('createFileModal').style.display = 'none';
    document.getElementById('fileName').value = '';
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Don't trigger shortcuts when typing in inputs
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
            return;
        }
        
        switch(event.key.toLowerCase()) {
            case 'u':
                event.preventDefault();
                showUploadModal();
                break;
            case 'n':
                event.preventDefault();
                showCreateFolderModal();
                break;
            case 'f':
                if (!event.ctrlKey && !event.metaKey) {
                    event.preventDefault();
                    showCreateFileModal();
                }
                break;
            case 'escape':
                // Close any open modal
                const openModal = document.querySelector('.modal[style*="display: block"]');
                if (openModal) {
                    openModal.style.display = 'none';
                }
                break;
        }
    });
}

// Export functions for HTML onclick
window.showUploadModal = showUploadModal;
window.closeUploadModal = closeUploadModal;
window.showCreateFolderModal = showCreateFolderModal;
window.closeCreateFolderModal = closeCreateFolderModal;
window.showCreateFileModal = showCreateFileModal;
window.closeCreateFileModal = closeCreateFileModal;
window.createFolder = createFolder;
window.createFile = createFile;
window.previewFile = previewFile;
window.downloadFile = downloadFile;
window.navigateTo = navigateTo;
window.downloadFolder = downloadFolder;
window.deleteItem = deleteItem;
window.closeDeleteModal = closeDeleteModal;
window.confirmDelete = confirmDelete;
window.startUpload = startUpload;
window.resetUploadForm = resetUploadForm;