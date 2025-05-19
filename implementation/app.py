import nltk
from flask import Flask, request, jsonify, render_template
import csv
import re
import pickle
from tensorflow.keras.models import load_model
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
from datetime import timedelta
import datetime
from collections import defaultdict, Counter
from nltk.stem import PorterStemmer
import os

# Download necessary NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

app = Flask(__name__)

# Load the model, tokenizer, and label encoder
model = load_model('lstm-2-new.h5')
with open('tokenizer-new.pkl', 'rb') as handle:
    tokenizer = pickle.load(handle)

# Define emotion labels directly
emotion_labels = ['anger', 'fear', 'joy', 'love', 'sadness', 'surprise']

# Preprocessing functions (same as in the notebook)
def basic_clean(text):
    text = re.sub(r'[^a-zA-Z ]', '', text)  # Keep only letters and spaces
    text = text.lower()                     # Convert to lowercase
    text = re.sub(r'\s+', ' ', text).strip()# Remove extra whitespace
    return text

def tokenize(text):
    return text.split()

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))
stemmer = PorterStemmer()

def preprocess_tokens(tokens): #di ko sure if tokens gid man ibutang di or text, nag ano ko sa gpt sakto man kuno ang tokens
    # Remove stopwords, lemmatize, then stem
    return [stemmer.stem(lemmatizer.lemmatize(word)) for word in tokens if word not in stop_words]

MAX_SEQUENCE_LENGTH = 100

@app.route('/')
def landing():
    return render_template('index.html')

@app.route('/diary')
def diary():
    now = datetime.datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    return render_template('landing.html', current_time=current_time)

@app.route('/save', methods=['POST'])
def save_diary_entry():
    diary_title = request.json['title']
    diary_entry = request.json['diary_entry']
    print(f"Diary entry received: Title: {diary_title}, Entry: {diary_entry}")

    # Preprocess the diary entry
    cleaned_text = basic_clean(diary_entry)
    print(f"Cleaned text: {cleaned_text}")
    tokens = tokenize(cleaned_text)
    print(f"Tokens: {tokens}")
    lemmatized_tokens = preprocess_tokens(tokens)
    print(f"Lemmatized tokens: {lemmatized_tokens}")
    padded_sequence = pad_sequences(tokenizer.texts_to_sequences([lemmatized_tokens]), maxlen=MAX_SEQUENCE_LENGTH, padding='post')
    print(f"Padded sequence shape: {padded_sequence.shape}")

    # Predict the emotion
    prediction = model.predict(padded_sequence)[0]
    
    # Print prediction probabilities for debugging
    for i, prob in enumerate(prediction):
        if i < len(emotion_labels): # Add this check
            print(f"  Probability for {emotion_labels[i]}: {prob:.4f}")
        else:
            print(f"  Probability for unknown label {i}: {prob:.4f}") # Handle potential mismatch

    # Define individual thresholds for each emotion
    emotion_thresholds = {
        'anger': 0.5,
        'fear': 0.5,
        'joy': 0.5,
        'love': 0.5,
        'sadness': 0.5,
        'surprise': 0.5,
        'neutral': 0.3 # A slightly lower threshold for neutral might be appropriate
    }

    # Determine predicted label based on individual thresholds
    predicted_emotion = 'neutral' # Default to neutral if no emotion meets the threshold
    max_probability = 0 # Start with 0 probability

    for i, prob in enumerate(prediction):
        if i < len(emotion_labels): # Ensure index is within bounds of defined labels
            label = emotion_labels[i]
            if prob >= emotion_thresholds.get(label, 0) and prob > max_probability:
                predicted_emotion = label
                max_probability = prob

    predicted_label = predicted_emotion
    print(f"Predicted emotion: {predicted_label}")

    # Generate feedback based on the predicted emotion
    feedback = generate_feedback(predicted_label)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save the diary entry to a CSV file
    try:
        with open('diary_entries.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Save timestamp, emotion, title, diary entry, and feedback
            writer.writerow([timestamp, predicted_label, diary_title, diary_entry, feedback[0]]) # Assuming feedback is a list, take the first element
        print("Diary entry saved successfully!")

        # Get the ID of the newly saved entry (line number)
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            entry_id = sum(1 for row in reader) # Get the total number of lines

    except Exception as e:
        print(f"Error saving diary entry: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    # Return the entry ID, emotion, and feedback
    return jsonify({'status': 'success', 'entry_id': entry_id, 'emotion': predicted_label, 'feedback': feedback[0]}) # Return feedback as string

def get_diary_entries():
    diary_entries = []
    try:
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                # Include the line number as the entry ID (1-based)
                diary_entries.append([i + 1] + row)
    except FileNotFoundError:
        pass
    return diary_entries

def get_diary_entry_by_id(entry_id):
    try:
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i + 1 == int(entry_id):
                    return [i + 1] + row # Return the entry with ID
    except FileNotFoundError:
        pass
    return None # Return None if entry not found

@app.route('/entries')
def show_entries():
    diary_entries = get_diary_entries()

    # Count the occurrences of each emotion
    emotion_counter = Counter()
    for entry in diary_entries:
        if len(entry) > 1:
            emotion = entry[1]  # Assuming [timestamp, emotion, title, text, feedback]
            emotion_counter[emotion] += 1

    return render_template('diary_entries.html', diary_entries=diary_entries, emotion_data=dict(emotion_counter))

@app.route('/entry/<int:entry_id>')
def show_single_entry(entry_id):
    entry = get_diary_entry_by_id(entry_id)
    if entry:
        return render_template('single_entry.html', entry=entry)
    else:
        return "Entry not found", 404 # Or render a custom error page

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
def delete_diary_entry(entry_id):
    entries = []
    try:
        with open('diary_entries.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                # Keep entries that do not match the entry_id (1-based index)
                if i + 1 != entry_id:
                    entries.append(row)
    except FileNotFoundError:
        pass # No entries to delete

    # Write the remaining entries back to the CSV file
    with open('diary_entries.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(entries)

    # Redirect back to the entries page
    from flask import redirect, url_for
    return redirect(url_for('show_entries'))


@app.route('/edit_entry/<int:entry_id>')
def edit_diary_entry(entry_id):
    entry = get_diary_entry_by_id(entry_id)
    if entry:
        return render_template('edit_entry.html', entry=entry)
    else:
        return "Entry not found", 404 # Or render a custom error page


@app.route('/update_entry/<int:entry_id>', methods=['POST'])
def update_diary_entry(entry_id):
    updated_title = request.form['title']
    updated_entry_text = request.form['diary_entry']

    entries = []
    try:
        with open('diary_entries.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                # Check if this is the entry to update (1-based index)
                if i + 1 == entry_id:
                    # Update the title and entry text (assuming structure: timestamp, emotion, title, entry, feedback)
                    row[2] = updated_title
                    row[3] = updated_entry_text
                    # Note: Emotion and feedback are not re-predicted on edit in this implementation
                entries.append(row)
    except FileNotFoundError:
        # If file not found, there's nothing to update
        pass

    # Write the updated entries back to the CSV file
    with open('diary_entries.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(entries)

    # Redirect to the single entry page for the updated entry
    from flask import redirect, url_for
    return redirect(url_for('show_single_entry', entry_id=entry_id))


def generate_feedback(emotion):
    # Define feedback messages for each emotion
    feedback_messages = {
        'anger': ["Take a deep breath and count to ten.", "Try to identify the source of your anger and address it directly."],
        'fear': ["Acknowledge your fear and try to understand its root cause.", "Practice relaxation techniques like meditation or deep breathing."],
        'joy': ["Embrace this feeling and share it with others.", "Reflect on what brought you this joy and try to incorporate more of it into your life."],
        'love': ["Express your love to those you care about.", "Cherish the moments you share with loved ones."],
        'sadness': ["Allow yourself to feel the sadness and don't try to suppress it.", "Talk to a friend or family member about how you're feeling."],
        'surprise': ["Embrace the unexpected and be open to new possibilities.", "Reflect on what surprised you and why."],
        'neutral': ["It seems like your diary entry doesn't express a strong emotion.", "Try to explore your feelings further."]
    }
    # Return a single feedback message (you might want to add logic to choose one)
    return feedback_messages.get(emotion, ["No feedback available for this emotion."])

@app.route("/data")
def get_data():
    data = []
    try:
        print("Looking in:", os.getcwd())
        with open('diary_entries.csv', newline='', encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=["timestamp", "emotion", "title", "entry", "feedback"])
            for row in reader:
                print("Row read:", row)  # Debug
                data.append({
                    "timestamp": row["timestamp"],
                    "emotion": row["emotion"],
                    "title": row["title"],
                    "entry": row["entry"],
                    "feedback": row["feedback"]
                })
    except Exception as e:
        print("Error reading CSV:", e)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
