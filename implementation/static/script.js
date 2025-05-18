console.log("script.js loaded and running");
// Add event listener for the save button on the diary entry page
const saveBtn = document.getElementById('saveBtn');
if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
        const diaryTitle = document.getElementById('diaryTitle').value;
        const diaryInput = document.getElementById('diaryInput').value;
        const feedbackArea = document.getElementById('feedbackArea');
        const emotionDisplay = document.getElementById('emotionDisplay');

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
                // Redirect to the single entry page after successful save
                window.location.href = `/entry/${result.entry_id}`;
            } else {
                feedbackArea.textContent = `Error saving entry: ${result.message}`;
                emotionDisplay.textContent = ''; // Clear emotion display on error
            }
        } catch (error) {
            console.error('Error:', error);
            feedbackArea.textContent = 'An error occurred while saving the entry.';
            emotionDisplay.textContent = ''; // Clear emotion display on error
        }
    });
}
