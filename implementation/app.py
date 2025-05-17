from flask import Flask, request, jsonify, render_template
import csv
import re
import pickle
from tensorflow.keras.models import load_model
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
import datetime

app = Flask(__name__)

# Load the model, tokenizer, and label encoder
model = load_model('lstm-2.h5')
with open('tokenizer.pkl', 'rb') as handle:
    tokenizer = pickle.load(handle)
with open('label_encoder.pkl', 'rb') as handle:
    label_encoder = pickle.load(handle)

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

def lemmatize_and_remove_stopwords(tokens):
    return [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]

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
    diary_entry = request.json['diary_entry']
    print(f"Diary entry received: {diary_entry}")

    # Preprocess the diary entry
    cleaned_text = basic_clean(diary_entry)
    tokens = tokenize(cleaned_text)
    lemmatized_tokens = lemmatize_and_remove_stopwords(tokens)
    padded_sequence = pad_sequences(tokenizer.texts_to_sequences([lemmatized_tokens]), maxlen=MAX_SEQUENCE_LENGTH, padding='post')
    print(f"Padded sequence shape: {padded_sequence.shape}")

    # Predict the emotion
    prediction = model.predict(padded_sequence)[0]

    # Set a threshold for emotion probabilities
    threshold = 0.5
    if np.max(prediction) < threshold:
        predicted_label = 'neutral'
    else:
        predicted_label = label_encoder.inverse_transform([np.argmax(prediction)])[0]
    print(f"Predicted emotion: {predicted_label}")

    # Generate feedback based on the predicted emotion
    feedback = generate_feedback(predicted_label)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save the diary entry to a CSV file
    try:
        with open('diary_entries.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, predicted_label, diary_entry])
        print("Diary entry saved successfully!")
    except Exception as e:
        print(f"Error saving diary entry: {e}")

    return jsonify({'emotion': predicted_label, 'feedback': feedback})

def get_diary_entries():
    diary_entries = []
    try:
        with open('diary_entries.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                diary_entries.append(row)
    except FileNotFoundError:
        pass
    return diary_entries

@app.route('/entries')
def show_entries():
    diary_entries = get_diary_entries()
    return render_template('diary_entries.html', diary_entries=diary_entries)

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
    return feedback_messages.get(emotion, ["No feedback available for this emotion."])

if __name__ == '__main__':
    app.run(debug=True)