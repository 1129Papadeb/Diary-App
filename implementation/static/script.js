console.log("script.js loaded and running");

// Add event listener for the save button on the diary entry page
const saveBtn = document.getElementById('saveBtn');
if (saveBtn) {
    // Add loading state to button
    const addLoadingState = (button) => {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
        return originalText;
    };

    // Remove loading state from button
    const removeLoadingState = (button, originalText) => {
        button.disabled = false;
        button.innerHTML = originalText;
    };

    saveBtn.addEventListener('click', async () => {
        const diaryTitle = document.getElementById('diaryTitle').value;
        const diaryInput = document.getElementById('diaryInput').value;
        const feedbackArea = document.getElementById('feedbackArea');
        const emotionDisplay = document.getElementById('emotionDisplay');
        
        // Validate input
        if (!diaryTitle.trim()) {
            showToast('Please enter a title for your diary entry', 'warning');
            return;
        }
        
        if (!diaryInput.trim() || diaryInput.trim().length < 5) {
            showToast('Please write a longer diary entry', 'warning');
            return;
        }

        // Show loading state
        const originalBtnText = addLoadingState(saveBtn);

        try {
            const response = await fetch('/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title: diaryTitle, diary_entry: diaryInput }),
            });

            const result = await response.json();

            if (result.status === 'success') {
                // Show success message
                showToast('Entry saved successfully!', 'success');
                
                // Redirect to the single entry page after successful save
                setTimeout(() => {
                    window.location.href = `/entry/${result.entry_id}`;
                }, 1000);
            } else {
                removeLoadingState(saveBtn, originalBtnText);
                feedbackArea.textContent = `Error saving entry: ${result.message}`;
                emotionDisplay.textContent = ''; // Clear emotion display on error
                showToast('Error saving entry', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            removeLoadingState(saveBtn, originalBtnText);
            feedbackArea.textContent = 'An error occurred while saving the entry.';
            emotionDisplay.textContent = ''; // Clear emotion display on error
            showToast('An error occurred', 'error');
        }
    });
}

// Character counter for diary input
const diaryInput = document.getElementById('diaryInput');
if (diaryInput) {
    // Create character counter element
    const counterContainer = document.createElement('div');
    counterContainer.className = 'text-sm text-gray-500 mt-2 flex justify-end';
    counterContainer.innerHTML = '<span>0 characters</span>';
    diaryInput.parentNode.appendChild(counterContainer);
    
    // Update counter on input
    diaryInput.addEventListener('input', () => {
        const count = diaryInput.value.length;
        counterContainer.innerHTML = `<span>${count} character${count !== 1 ? 's' : ''}</span>`;
        
        // Change color based on length
        if (count > 300) {
            counterContainer.className = 'text-sm text-green-600 mt-2 flex justify-end';
        } else if (count > 100) {
            counterContainer.className = 'text-sm text-blue-600 mt-2 flex justify-end';
        } else {
            counterContainer.className = 'text-sm text-gray-500 mt-2 flex justify-end';
        }
    });
    
    // Add auto-resize functionality
    diaryInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
}

// Toast notification system
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col space-y-2';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    
    // Set toast classes based on type
    let iconClass = 'fas fa-info-circle';
    let bgColor = 'bg-blue-500';
    
    switch(type) {
        case 'success':
            iconClass = 'fas fa-check-circle';
            bgColor = 'bg-green-500';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle';
            bgColor = 'bg-yellow-500';
            break;
        case 'error':
            iconClass = 'fas fa-times-circle';
            bgColor = 'bg-red-500';
            break;
    }
    
    toast.className = `${bgColor} text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-fade-in`;
    toast.innerHTML = `
        <i class="${iconClass}"></i>
        <span>${message}</span>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0', 'transition-opacity', 'duration-300');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Mobile menu toggle
const mobileMenuButton = document.getElementById('mobile-menu-button');
const mobileMenu = document.getElementById('mobile-menu');

if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', () => {
        mobileMenu.classList.toggle('hidden');
    });
}
