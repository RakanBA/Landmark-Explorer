import os
from dotenv import load_dotenv
import streamlit as st
import requests
import cv2
import numpy as np
from PIL import Image
import uuid
import re

# Load environment variables from the .env file
load_dotenv()

# Custom Vision API details
CV_API_URL = os.getenv('CV_API_URL')
CV_API_KEY = os.getenv('CV_API_KEY')

# Azure GPT-4o-mini API details
GPT4_API_URL = os.getenv('GPT4_API_URL')
GPT_API_KEY = os.getenv('GPT_API_KEY')

# Microsoft Translator API details
TRANSLATOR_KEY = os.getenv('TRANSLATOR_KEY')
TRANSLATOR_ENDPOINT = os.getenv('TRANSLATOR_ENDPOINT')
TRANSLATOR_LOCATION = os.getenv('TRANSLATOR_LOCATION', 'eastus')

# Streamlit app configuration
st.set_page_config(page_title="Landmark Explorer", page_icon="🌍", layout="wide")

# Enhanced Function to Translate Text
def translate_text(text, target_language):
    """
    Translate text to a specified target language using the Translator API.
    Handles API calls and errors gracefully.
    """
    path = '/translate'
    constructed_url = TRANSLATOR_ENDPOINT + path
    params = {
        'api-version': '3.0',
        'from': 'en',
        'to': [target_language.lower()]
    }
    headers = {
        'Ocp-Apim-Subscription-Key': TRANSLATOR_KEY,
        'Ocp-Apim-Subscription-Region': TRANSLATOR_LOCATION,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    body = [{'text': text}]

    try:
        # Make the API request
        response = requests.post(constructed_url, params=params, headers=headers, json=body)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the response
        response_data = response.json()
        if response_data:
            translation = response_data[0].get("translations", [])[0].get("text", "")
            return translation
        else:
            st.error("No response from the translation service.")
            return ""

    except requests.exceptions.RequestException as e:
        # Handle errors such as network issues or API failure
        st.error("Translation failed. Please check your network or API settings, or try again later.")
        return f"Error: {str(e)}"

def clean_translation(translation):
    """Remove '**' markers from the translation text."""
    return re.sub(r"\*\*(.*?)\*\*", r"\1", translation)

# Streamlit App Title and Intro
st.markdown(
    """
    <style>
    body {
        background-color: #1e1e2f;
    }
    .app-title {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #f4f4f9;
        margin-bottom: 10px;
        text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.2);
    }
    .app-description {
        font-size: 1.8rem;
        text-align: center;
        color: #d1d1e3;
        margin-bottom: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="app-title">Landmark Explorer', unsafe_allow_html=True)
st.markdown('<div class="app-description">Upload or capture an image to identify landmarks and get multilingual information.', unsafe_allow_html=True)

# Settings Section
st.sidebar.header("⚙️ Settings")

with st.sidebar:
    # Add the translation option checkbox before the language selection dropdown
    translate_option = st.checkbox("Would you like to translate the response?", value=True)

    # Add the language dropdown to appear after the checkbox
    selected_language = st.selectbox("🌍 Select the language for translations:", ["en", "ar", "fr", "es", "zh", "de"])

    option = st.radio("🖼️ How would you like to provide an image?", ("Upload Image", "Use Camera"), key="image_option")

# Image Input Section
st.markdown(
    """
    <style>
    .radio-option {
        font-weight: bold;
        color: #2c3e50;
    }
    </style>
    """,
    unsafe_allow_html=True
)

with st.container():
    image = None

    if option == "Use Camera":
        camera_input = st.camera_input("Capture an Image")
        if camera_input:
            image = Image.open(camera_input)

    elif option == "Upload Image":
        uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image = Image.open(uploaded_file)

# Display and Process Image
if image:
    st.markdown(
        """
        <style>
        .image-display {
            text-align: center;
            margin-top: 20px;
            border: 2px solid #34495e;
            border-radius: 15px;
            box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.15);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="image-display">', unsafe_allow_html=True)
    st.image(image, caption="Selected Image", use_container_width=True)

    image_bytes = cv2.imencode('.jpg', np.array(image))[1].tobytes()

    # Send the image to Custom Vision API
    headers_cv = {
        "Prediction-Key": CV_API_KEY,
        "Content-Type": "application/octet-stream"
    }

    st.write("🔍 Analyzing the image using the Custom Vision API...")
    response_cv = requests.post(CV_API_URL, headers=headers_cv, data=image_bytes)

    if response_cv.status_code == 200:
        predictions = response_cv.json().get("predictions", [])
        if predictions:
            predictions = sorted(predictions, key=lambda x: x["probability"], reverse=True)
            top_prediction = predictions[0]
            tag = top_prediction["tagName"]
            confidence = top_prediction["probability"]

            if confidence > 0.65 and tag.lower() != "negative":
                st.markdown(f'<div class="landmark-info" style="color: white; background-color: #0f121a; border: none; padding: 10px 20px; border-radius: 10px; font-size: 28px; text-align: center; font-weight: bold;">Landmark Name: {tag}</div>', unsafe_allow_html=True)

                # Enhanced Styling for Learn More About This Landmark Section
                st.write("### 📚 Learn More About This Landmark")
                query = None
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    if st.button("📝 Description", key="description_button", help="Get a concise description of the landmark"):
                        query = f"Give me a short description of {tag}."
                with col2:
                    if st.button("📖 Historical Background", key="history_button", help="Learn about the historical significance of the landmark"):
                        query = f"Give a brief history of {tag}."
                with col3:
                    if st.button("🎉 Fun Facts", key="fun_facts_button", help="Discover interesting facts about the landmark"):
                        query = f"Give some fun facts about {tag}."
                with col4:
                    if st.button("🌍 Nearby Attractions", key="nearby_attractions_button", help="Find nearby attractions or landmarks"):
                        query = f"What are nearby attractions around {tag}?"

                # Handle Query and Display Results with Enhanced Parameters and System Prompt
                if query:
                    st.write(f"🤔 Generating response about **{tag}**...")

                    headers_gpt4 = {
                        "Content-Type": "application/json",
                        "api-key": GPT_API_KEY
                    }

                    # Use the updated system prompt that encourages conciseness and engaging formatting
                    system_prompt = (
                        "You are a knowledgeable assistant for landmarks, providing concise, simple, and exciting descriptions. "
                        "Imagine you're talking to a tourist, and your goal is to make them thrilled to visit this landmark. "
                        "Keep the information as short as possible, without exceeding 250 tokens, but use fewer tokens if appropriate. "
                        "Write in a way that is easy to read—use bullet points, short paragraphs, and simple language. "
                        "Make the description positive, engaging, and informative, highlighting key aspects that make the landmark special."
                    )

                    data_gpt4 = {
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query}
                        ],
                        "max_tokens": 250,  # Set a maximum token limit to 250 to prevent overly long responses
                        "temperature": 0.8,  # Increase temperature to add excitement to the response
                        "top_p": 0.9         # Use top_p sampling for diverse and engaging responses
                    }

                    try:
                        response_gpt4 = requests.post(GPT4_API_URL, headers=headers_gpt4, json=data_gpt4)
                        response_gpt4.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx

                        # Extract the content from the response
                        response_data = response_gpt4.json()
                        if "choices" in response_data and len(response_data["choices"]) > 0:
                            result = response_data["choices"][0]["message"]["content"].strip()
                            st.markdown(f"### 📝 Response for {tag}")
                            st.write(result)

                            # Translation Section
                            if translate_option and selected_language != "en":
                                st.markdown(f"### 🌍 Translation ({selected_language.upper()})")
                                translation = translate_text(result, selected_language)
                                cleaned_translation = clean_translation(translation)

                                if selected_language == "ar":
                                    st.markdown(
                                        f"""
                                        <div style="direction: rtl; text-align: right;">
                                            {cleaned_translation}
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.markdown(cleaned_translation)
                        else:
                            st.error("⚠️ Unexpected response format from GPT-4 API. Please try again later.")

                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ An error occurred: {e}")
                        if st.button("🔄 Retry"):
                            st.set_page_config()  # Refreshes the page to reset the app state
            else:
                st.warning("⚠️ No recognizable landmark detected in the image. Please try uploading a different image.")
                if st.button("🔄 Try Again"):
                    st.set_page_config()  # Refreshes the page to reset the app state
        else:
            st.warning("⚠️ No predictions received from the model. Please try uploading a different image.")
            if st.button("🔄 Try Again"):
                st.set_page_config()  # Refreshes the page to reset the app state
    else:
        st.error(f"❌ Error: {response_cv.status_code}. Please try again later.")

else:
    st.info("☝️ Please provide an image to analyze.")
