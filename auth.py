import streamlit as st
import pickle
import os.path
from datetime import datetime, timedelta

class Authenticator:
    def __init__(self):
        self.users_db_file = 'users.pkl'
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.users_db_file):
            with open(self.users_db_file, 'rb') as f:
                return pickle.load(f)
        return {
            'admin': {
                'password': 'admin123',  # Change this default password
                'email': 'admin@example.com',
                'created_at': datetime.now()
            }
        }

    def save_users(self):
        with open(self.users_db_file, 'wb') as f:
            pickle.dump(self.users, f)

    def login(self, username, password):
        if username in self.users and self.users[username]['password'] == password:
            return True
        return False

    def register(self, username, password, email):
        if username in self.users:
            return False, "Username already exists"
        
        self.users[username] = {
            'password': password,
            'email': email,
            'created_at': datetime.now()
        }
        self.save_users()
        return True, "Registration successful"

    def reset_password(self, username, email):
        if username in self.users and self.users[username]['email'] == email:
            # Here you would typically send an email with reset link
            # For demo, we'll just reset to a default password
            self.users[username]['password'] = 'resetpass123'
            self.save_users()
            return True, "Password has been reset to: resetpass123"
        return False, "Invalid username or email"

def login_page():
    st.title("Login")
    
    # Initialize the authenticator
    auth = Authenticator()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
        
        with tab1:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login"):
                if auth.login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with tab2:
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_email = st.text_input("Email", key="reg_email")
            
            if st.button("Register"):
                success, message = auth.register(reg_username, reg_password, reg_email)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        with tab3:
            reset_username = st.text_input("Username", key="reset_username")
            reset_email = st.text_input("Email", key="reset_email")
            
            if st.button("Reset Password"):
                success, message = auth.reset_password(reset_username, reset_email)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    return st.session_state.authenticated

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
