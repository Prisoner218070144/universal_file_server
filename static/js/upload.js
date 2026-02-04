// Upload functionality for Universal File Server
let selectedFiles = [];
let isUploading = false;

function initUploadHandlers() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    if (!dropZone || !fileInput) return;
    
    // Click to browse
    dropZone.addEventListener('click', (e) => {
        if (e.target !== dropZone && e.target.className !== 'btn-browse') {
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
        dropZone.classList.add('dragover');
        dropZone.style.borderColor = '#4CAF50';
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
        dropZone.style.borderColor = '#444';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
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
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`Folder "${folderName}" created successfully`);
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
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`File "${fileName}" created successfully`);
            window.location.reload();
        } else {
            alert(`Error creating file: ${data.error || 'Unknown error'}`);
        }
    })
    .catch(error => {
        alert('Error creating file: ' + error.message);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initUploadHandlers();
    
    // Set focus to input when modal opens
    const folderModal = document.getElementById('createFolderModal');
    const fileModal = document.getElementById('createFileModal');
    
    if (folderModal) {
        folderModal.addEventListener('shown', function() {
            const input = document.getElementById('folderName');
            if (input) input.focus();
        });
    }
    
    if (fileModal) {
        fileModal.addEventListener('shown', function() {
            const input = document.getElementById('fileName');
            if (input) input.focus();
        });
    }
    
    // Set up keyboard shortcuts for modals
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (document.getElementById('uploadModal').style.display === 'block') {
                closeUploadModal();
            }
            if (document.getElementById('createFolderModal').style.display === 'block') {
                closeCreateFolderModal();
            }
            if (document.getElementById('createFileModal').style.display === 'block') {
                closeCreateFileModal();
            }
        }
    });
});

// Make functions globally available
window.initUploadHandlers = initUploadHandlers;
window.handleFiles = handleFiles;
window.startUpload = startUpload;
window.resetUploadForm = resetUploadForm;
window.createFolder = createFolder;
window.createFile = createFile;