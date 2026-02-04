document.addEventListener('DOMContentLoaded', function() {
    // Focus on search input
    const searchInput = document.querySelector('.search-box');
    if (searchInput) {
        searchInput.focus();
        // Select all text for easy editing
        searchInput.select();
    }
    
    // Handle keyboard shortcuts for search
    document.addEventListener('keydown', function(event) {
        // Ctrl+F or Cmd+F to focus search
        if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
            event.preventDefault();
            const searchBox = document.querySelector('.search-box');
            if (searchBox) searchBox.focus();
        }
        
        // Escape to clear search
        if (event.key === 'Escape') {
            const searchBox = document.querySelector('.search-box');
            if (searchBox && searchBox === document.activeElement) {
                searchBox.value = '';
                searchBox.blur();
            }
        }
    });
});

// Function to navigate to a folder
function navigateTo(path) {
    const encodedPath = encodeURIComponent(path).replace(/%2F/g, '/');
    window.location.href = '/browse/' + encodedPath;
}

// Function to preview a file
function previewFile(filePath) {
    window.location.href = '/preview/' + encodeURIComponent(filePath);
}

// Function to open file
function openFile(path, action) {
    event.stopPropagation();
    
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

// Function to download folder
function downloadFolder(path) {
    event.stopPropagation();
    
    if (!confirm(`Download the entire folder "${path.split('/').pop() || 'F Drive'}"? This may take a while for large folders.`)) {
        return;
    }
    
    const encodedPath = encodeURIComponent(path);
    window.location.href = '/download_folder/' + encodedPath;
}

// Function to delete item
function deleteItem(itemPath, type) {
    event.stopPropagation();
    
    const itemName = itemPath.split('/').pop();
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'deleteModal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Confirm Delete</h3>
            <p>Are you sure you want to delete "<span id="deleteItemName">${itemName}</span>"?</p>
            <p class="warning-text" id="deleteWarning">
                ${type === 'folder' ? 'This will delete the folder and all its contents.' : 'This action cannot be undone.'}
            </p>
            <div class="modal-actions">
                <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn-danger" onclick="confirmDelete('${itemPath}')">Delete</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.remove();
    }
}

function confirmDelete(itemPath) {
    fetch('/delete/' + encodeURIComponent(itemPath), {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Item deleted successfully');
            window.location.reload();
        } else {
            alert('Error deleting: ' + data.error);
        }
        closeModal();
    })
    .catch(error => {
        alert('Error deleting');
        closeModal();
    });
}