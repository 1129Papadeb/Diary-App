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
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random

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
model = load_model('lstm-2.h5')
with open('tokenizer.pkl', 'rb') as handle:
    tokenizer = pickle.load(handle)

# Define emotion labels directly
emotion_labels = ['anger', 'fear', 'joy', 'love', 'sadness', 'surprise']

# Load quotes from CSV
def load_quotes():
    quotes = []
    with open('quotes.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            quotes.append({
                'author': row['Author'],
                'quote': row['Quote']
            })
    return quotes

# Initialize TF-IDF vectorizer
tfidf = TfidfVectorizer(stop_words='english')

# Preprocessing functions
def basic_clean(text):
    text = re.sub(r'[^a-zA-Z ]', '', text)  # Keep only letters and spaces
    text = text.lower()                     # Convert to lowercase
    text = re.sub(r'\s+', ' ', text).strip()# Remove extra whitespace
    return text

def tokenize(text):
    return text.split()

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def preprocess_tokens(tokens):
    return [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]

def find_matching_quote(text, quotes):
    # Create corpus of quotes
    quote_texts = [q['quote'] for q in quotes]
    
    # Fit TF-IDF on quotes and transform both quotes and input text
    tfidf_matrix = tfidf.fit_transform(quote_texts)
    text_vector = tfidf.transform([text])
    
    # Calculate similarities
    similarities = cosine_similarity(text_vector, tfidf_matrix)[0]
    
    # Get index of most similar quote
    best_match_idx = np.argmax(similarities)
    
    return quotes[best_match_idx]

MAX_SEQUENCE_LENGTH = 100

@app.route('/')
def landing():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

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
        if i < len(emotion_labels):
            print(f"  Probability for {emotion_labels[i]}: {prob:.4f}")
        else:
            print(f"  Probability for unknown label {i}: {prob:.4f}")

    # Define individual thresholds for each emotion
    emotion_thresholds = {
        'anger': 0.5,
        'fear': 0.5,
        'joy': 0.5,
        'love': 0.5,
        'sadness': 0.5,
        'surprise': 0.5,
        'neutral': 0.3
    }

    # Determine predicted label based on individual thresholds
    predicted_emotion = 'neutral'
    max_probability = 0

    for i, prob in enumerate(prediction):
        if i < len(emotion_labels):
            label = emotion_labels[i]
            if prob >= emotion_thresholds.get(label, 0) and prob > max_probability:
                predicted_emotion = label
                max_probability = prob

    predicted_label = predicted_emotion
    print(f"Predicted emotion: {predicted_label}")

    # Generate feedback based on the predicted emotion
    feedback = generate_feedback(predicted_label, diary_entry)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save the diary entry to a CSV file
    try:
        with open('diary_entries.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, predicted_label, diary_title, diary_entry, feedback])
        print("Diary entry saved successfully!")

        # Get the ID of the newly saved entry (line number)
        entry_id = 0
        try:
            with open('diary_entries.csv', 'r') as csvfile:
                reader = csv.reader(csvfile)
                entry_id = sum(1 for row in reader)
        except Exception as e:
            print(f"Error counting entries: {e}")
            entry_id = 1

    except Exception as e:
        print(f"Error saving diary entry: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'success', 'entry_id': entry_id, 'emotion': predicted_label, 'feedback': feedback})

def get_diary_entries():
    diary_entries = []
    try:
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                diary_entries.append([i + 1] + row)
        
        diary_entries.sort(key=lambda x: x[1], reverse=True)
    except FileNotFoundError:
        pass
    return diary_entries

def get_diary_entry_by_id(entry_id):
    try:
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i + 1 == int(entry_id):
                    return [i + 1] + row
    except FileNotFoundError:
        pass
    return None

@app.route('/entries')
def show_entries():
    diary_entries = get_diary_entries()
    emotion_counter = Counter()
    for entry in diary_entries:
        if len(entry) > 1:
            emotion = entry[2]
            emotion_counter[emotion] += 1
    return render_template('diary_entries.html', diary_entries=diary_entries, emotion_data=dict(emotion_counter))

@app.route('/entry/<int:entry_id>')
def show_single_entry(entry_id):
    entry = get_diary_entry_by_id(entry_id)
    if entry:
        return render_template('single_entry.html', entry=entry)
    else:
        return "Entry not found", 404

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
def delete_diary_entry(entry_id):
    entries = []
    try:
        with open('diary_entries.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i + 1 != entry_id:
                    entries.append(row)
    except FileNotFoundError:
        pass

    with open('diary_entries.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(entries)

    from flask import redirect, url_for
    return redirect(url_for('show_entries'))

@app.route('/edit_entry/<int:entry_id>')
def edit_diary_entry(entry_id):
    entry = get_diary_entry_by_id(entry_id)
    if entry:
        return render_template('edit_entry.html', entry=entry)
    else:
        return "Entry not found", 404

@app.route('/update_entry/<int:entry_id>', methods=['POST'])
def update_diary_entry(entry_id):
    updated_title = request.form['title']
    updated_entry_text = request.form['diary_entry']

    entries = []
    try:
        with open('diary_entries.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i + 1 == entry_id:
                    row[2] = updated_title
                    row[3] = updated_entry_text
                entries.append(row)
    except FileNotFoundError:
        pass

    with open('diary_entries.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(entries)

    from flask import redirect, url_for
    return redirect(url_for('show_single_entry', entry_id=entry_id))

def generate_feedback(emotion, text):
    quotes = load_quotes()
    matching_quote = find_matching_quote(text, quotes)

    # Longer, varied feedback options per emotion
    feedback_messages_multi = {
        'anger': [
            "It's perfectly valid to feel anger when things go wrong. Try to sit with the feeling and express it in healthy ways.",
            "Anger can be overwhelming, but it's often a sign that something important to you needs attention. Take time to understand it.",
            "You’re feeling angry, and that’s okay. Deep breaths and self-compassion can help you manage it constructively."
        ],
        'fear': [
            "Fear is a natural response to uncertainty. Acknowledge it, and take one small step at a time forward.",
            "It’s okay to be afraid — you're not alone. Facing your fears slowly can build strength and confidence.",
            "Your fear matters. Use it as a signal, not a stop sign, and proceed with kindness toward yourself."
        ],
        'joy': [
            "Joy is a beautiful feeling. Let yourself experience it fully and remember what brought you here.",
            "Moments of happiness are precious. Bask in it and share it with others when you can.",
            "You're feeling joyful — that's wonderful. Take a mental snapshot of this moment for future reflection."
        ],
        'love': [
            "Love connects us and makes life meaningful. Treasure the moments and people that bring you closer.",
            "You're surrounded by loving energy — let it lift you and inspire kindness in return.",
            "Love can bring clarity, comfort, and strength. Hold on to it, and let it guide your next step."
        ],
        'sadness': [
            "Sadness isn't a weakness — it’s a sign that something matters. Give yourself permission to feel and heal.",
            "It's okay to feel down sometimes. Let the emotions come and go like waves — you are not alone.",
            "You're experiencing sadness. Be gentle with yourself, and take your time. Healing is not a race."
        ],
        'surprise': [
            "Surprises can shake your expectations. Stay curious — the unknown may hold something meaningful.",
            "Life just threw something unexpected your way. Pause, process, and see what it might be teaching you.",
            "Unexpected moments can be both unsettling and eye-opening. Keep an open heart and observe what unfolds."
        ],
        'neutral': [
            "Sometimes we just feel okay — not great, not bad. It's a good time to reflect and recharge.",
            "This seems like a moment of calm. Use it to check in with yourself and gather energy for what’s ahead.",
            "Neutral days can offer clarity and quiet strength. Appreciate the stillness and space it provides."
        ]
    }

    # Pick random feedback from the list for the emotion
    feedback_text = random.choice(feedback_messages_multi.get(emotion, ["Your feelings are valid. Take care of yourself."]))

    # Format feedback response
    feedback = (
        f" {feedback_text}\n\n"
        f"Remember:\n\n\"{matching_quote['quote']}\"\n\n— {matching_quote['author'] or 'Unknown'}"
    )
    return feedback
@app.route("/data")
def get_data():
    data = []
    try:
        print("Looking in:", os.getcwd())
        with open('diary_entries.csv', newline='', encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=["timestamp", "emotion", "title", "entry", "feedback"])
            for row in reader:
                print("Row read:", row)
                data.append({
                    "timestamp": row["timestamp"],
                    "emotion": row["emotion"],
                    "title": row["title"],
                    "entry": row["entry"],
                    "feedback": row["feedback"]
                })
        
        data.sort(key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        print("Error reading CSV:", e)
    return jsonify(data)

@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',      # or '127.0.0.1' if only local access is needed
        port=5000,           # any port you like (default is 5000)
        debug=False,         # turn off debugger to prevent reload loops
        use_reloader=False   # <- THIS is key to stop infinite reloads
    )