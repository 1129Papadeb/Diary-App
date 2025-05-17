document.getElementById('saveBtn').addEventListener('click', function() {
    const diaryEntry = document.getElementById('diaryInput').value;
    const diaryInput = document.getElementById('diaryInput');
    const saveBtn = document.getElementById('saveBtn');
    const emotionDisplay = document.getElementById('emotionDisplay');
    const feedbackArea = document.getElementById('feedbackArea');

    // Send the diary entry to the Flask API for prediction and saving
    fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ diary_entry: diaryEntry })
    })
    .then(response => response.json())
    .then(data => {
        // Check if the API returned the expected data
        if (!data || !data.emotion || !data.feedback) {
            console.error('Error: Invalid API response:', data);
            alert('Error processing diary entry: Invalid API response.');
            return;
        }

        // Display the predicted emotion and feedback
        diaryInput.style.display = 'none';
        saveBtn.style.display = 'none';

        const now = new Date();
        const dateTimeString = now.toLocaleString();

        const diaryDisplay = document.createElement('p');
        diaryDisplay.innerText = 'Diary Entry: ' + diaryEntry;

        const dateTimeDisplay = document.createElement('p');
        dateTimeDisplay.innerText = 'Date and Time: ' + dateTimeString;

        emotionDisplay.innerText = 'Emotion: ' + data.emotion;
        feedbackArea.innerText = 'Feedback: ' + data.feedback.join(' ');

        document.querySelector('.container').appendChild(dateTimeDisplay);
        document.querySelector('.container').appendChild(diaryDisplay);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error processing diary entry.');
    });
});