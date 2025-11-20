import json
import os
import pickle
import streamlit as st
import time
import requests
import logging

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Secure Auth Handling ---
try:
    import database
    DB_CONNECTED = True
except ImportError:
    st.error("⚠️ Could not find 'database.py'. Authentication will not work.")
    DB_CONNECTED = False

# --- API Keys and Constants ---
TMDB_API_KEY = "53b6d867536ea45efc9f95dbb1c2ced5"
DEFAULT_POSTER_URL = "https://placehold.co/500x750/3f3f46/FFFFFF?text=Poster+Unavailable"

GEMINI_API_KEY = "AIzaSyCYSxkL6DppzPr7qiMr5abYMlA0FXougpU"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"
)

# --- Session State Initialization ---
for key, default in {
    "bg_color": "black",
    "page": "main",
    "logged_in": False,
    "username": "",
    "user_type": None,
    "loaded": False,
    "chat_history": [ {
        "role": "model",
        "parts": [{"text": "Hello! I am CineMind, your AI movie expert. Ask me for recommendations, trivia, or anything about movies!"}]
    } ],
}.items():
    st.session_state.setdefault(key, default)

# --- Utility Functions ---
def back_to_home_button():
    if st.button("⬅️ Back to Recently Watched"):
        st.session_state['page'] = 'recently_watched'

def loading_page():
    st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:70vh;">
            <h1 style="font-size:4em;color:#e50914;">Cini Magic</h1>
            <p style="font-size:1.5em;color:#a1a1aa;">Your Movie Recommendation Companion</p>
            <div class="loader"></div>
        </div>
        <style>
        .loader {
            border:8px solid #3f3f46;
            border-top:8px solid #e50914;
            border-radius:50%;
            width:60px;height:60px;
            animation:spin 1s linear infinite;
            margin-top:2em;
        }
        @keyframes spin {0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
        </style>
    """, unsafe_allow_html=True)
    time.sleep(2)

def fetch_poster(movie_title, api_key=TMDB_API_KEY):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": api_key, "query": movie_title}
    try:
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
        if data.get("results") and data["results"][0].get("poster_path"):
            return f"https://image.tmdb.org/t/p/w500{data['results'][0]['poster_path']}"
    except Exception as e:
        logging.error(f"Poster fetch error: {e}")
    return DEFAULT_POSTER_URL

def fetch_new_movies():
    url = "https://api.themoviedb.org/3/movie/now_playing"
    params = {"api_key": TMDB_API_KEY, "language": "en-US", "page": 1}
    try:
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
        return [m["title"] for m in data.get("results", [])[:5]]
    except Exception as e:
        logging.error(f"Error fetching new movies: {e}")
        return ["No new movies found"]

def generate_chat_response(prompt):
    st.session_state.chat_history.append({"role": "user", "parts": [{"text": prompt}]})
    payload = {
        "contents": st.session_state.chat_history,
        "tools": [{"google_search": {}}],
        "systemInstruction": {
            "parts": [{"text": "You are CineMind, a witty, friendly AI movie expert. Keep answers concise and cinema-focused."}]
        }
    }
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        response.raise_for_status()
        result = response.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Error: no response.")
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": text}]})
        return text
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        return "There was a problem connecting to CineMind."

def recommend(movie, movies, similarity):
    try:
        idx = movies[movies['title'] == movie].index[0]
        distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])
        return [movies.iloc[i[0]]['title'] for i in distances[1:6]]
    except Exception as e:
        st.error(f"Recommendation error: {e}")
        return []

# --- Sidebar Profile ---
def user_profile_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div style='text-align: center; margin-top: 10px;'>
                <img src='https://api.dicebear.com/7.x/avataaars/svg?seed={st.session_state.get("username","User")}' 
                     width='100' height='100' 
                     style='border-radius: 50%; border: 2px solid #e50914;'>
                <h3 style='color: #e50914; margin-top: 10px;'>{st.session_state.get("username","User")}</h3>
                <p style='color: #a1a1aa; font-size: 0.9em;'>Movie Enthusiast 🍿</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🏠 Recently Watched"):
            st.session_state['page'] = 'recently_watched'
        if st.button("🎬 Recommendations"):
            st.session_state['page'] = 'recommendation'
        if st.button("🤖 Chatbot"):
            st.session_state['page'] = 'chatbot'
        if st.button("🌟 Favorites (Coming Soon)"):
            st.info("This feature will be added in the next version!")
        st.markdown("---")
        if st.button("🚪 Log Out"):
            st.session_state.update({
                "logged_in": False,
                "user_type": None,
                "username": "",
                "page": "main"
            })

# --- Pages ---
def user_selection_page():
    st.markdown("""
        <div style="text-align:center;padding-top:4rem;">
            <h1 style="color:#e50914;">Cini Magic</h1>
            <p style="color:#a1a1aa;">Your gateway to personalized movie recommendations.</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("user_selection_form"):
        st.subheader("Welcome Back!")
        existing = st.form_submit_button("➡️ Log In (Existing User)")
        new = st.form_submit_button("✨ Create Account (New User)")
        if existing:
            st.session_state['user_type'] = "existing"
        elif new:
            st.session_state['user_type'] = "new"

def login_page():
    st.markdown("<h2 style='color:#e50914;text-align:center;'>Cini Magic Login</h2>", unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if not username or not password:
            st.error("Please enter both username and password.")
        elif DB_CONNECTED and database.login_user(username, password):
            st.success("Login successful!")
            st.session_state.update({
                "logged_in": True,
                "username": username,
                "user_type": None,
                "page": "recently_watched"
            })
        else:
            st.error("Invalid username or password.")
    if st.button("Sign Up"):
        st.session_state['user_type'] = "new"

def sign_up_page():
    st.title("Sign Up for Cini Magic")
    with st.form("signup_form"):
        username = st.text_input("Choose a Username")
        password = st.text_input("Choose a Password", type="password")
        submit = st.form_submit_button("Create Account")
        if submit:
            if not username or not password:
                st.error("Username and password cannot be empty.")
            elif DB_CONNECTED and database.add_userdata(username, password):
                st.success("Account created! Please log in.")
                st.session_state['user_type'] = "existing"
            else:
                st.error("Username already exists or database error.")

def recommendation_page():
    user_profile_sidebar()
    back_to_home_button()
    st.markdown(f"<h2 style='color:#e50914;'>Recommendations for {st.session_state['username']}</h2>", unsafe_allow_html=True)
    try:
        movies = pickle.load(open('artificats/movie_list.pkl', 'rb'))
        similarity = pickle.load(open('artificats/similarity.pkl', 'rb'))
    except FileNotFoundError:
        st.error("Missing model files in 'artifacts/'.")
        return
    movie_list = movies['title'].values
    selected_movie = st.selectbox("Select a movie", movie_list)
    if st.button("Show Recommendation"):
        recs = recommend(selected_movie, movies, similarity)
        st.session_state['recently_watched'] = recs
        cols = st.columns(5)
        for i, col in enumerate(cols):
            if i < len(recs):
                with col:
                    st.image(fetch_poster(recs[i]), use_container_width=True)
                    st.caption(recs[i])

def chatbot_page():
    user_profile_sidebar()
    back_to_home_button()
    st.markdown("<h2 style='color:#e50914;'>CineMind Chatbot 🤖</h2>", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        avatar = "🤖" if msg["role"] == "model" else "😀"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["parts"][0]["text"])
    if prompt := st.chat_input("Ask CineMind..."):
        with st.chat_message("user", avatar="😀"):
            st.markdown(prompt)
        with st.chat_message("model", avatar="🤖"):
            with st.spinner("CineMind is thinking..."):
                reply = generate_chat_response(prompt)
                st.markdown(reply)

def recently_watched_page():
    user_profile_sidebar()
    st.markdown(f"## 🎞️ Recently Watched by {st.session_state['username']}")
    watched = st.session_state.get('recently_watched', [])
    if not watched:
        st.info("You haven't searched for any movies yet.")
    else:
        cols = st.columns(min(5, len(watched)))
        for i, col in enumerate(cols):
            with col:
                st.image(fetch_poster(watched[i]), use_container_width=True)
                st.caption(watched[i])
    st.markdown("---")
    st.subheader("Now Playing")
    new_movies = fetch_new_movies()
    cols = st.columns(len(new_movies))
    for i, col in enumerate(cols):
        with col:
            st.image(fetch_poster(new_movies[i]), use_container_width=True)
            st.caption(new_movies[i])
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎬 Go to Recommendations"):
            st.session_state['page'] = 'recommendation'
    with col2:
        if st.button("🤖 Talk to CineMind Chatbot"):
            st.session_state['page'] = 'chatbot'

# --- Main Routing ---
if not st.session_state['loaded']:
    loading_page()
    st.session_state['loaded'] = True

if not st.session_state['logged_in']:
    if st.session_state['user_type'] == "new":
        sign_up_page()
    elif st.session_state['user_type'] == "existing":
        login_page()
    else:
        user_selection_page()
else:
    if st.session_state['page'] == 'recently_watched':
        recently_watched_page()
    elif st.session_state['page'] == 'recommendation':
        recommendation_page()
    elif st.session_state['page'] == 'chatbot':
        chatbot_page()
    else:
        recently_watched_page()
