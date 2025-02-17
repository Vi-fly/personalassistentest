import streamlit as st
import json
import os
from main import master_process_command

# Configure page settings
st.set_page_config(
    page_title="Personal Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Dark mode custom styling
st.markdown("""
    <style>
    body {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        max-width: 80%;
        font-size: 16px;
    }
    .user-message {
        background-color: #0d47a1;
        color: #ffffff;
        text-align: left;
        margin-left: 20%;
    }
    .bot-message {
        background-color: #424242;
        color: #ffffff;
        text-align: left;
        margin-right: 20%;
    }
    .stTextInput input {
        border-radius: 25px;
        padding: 15px 20px;
        background-color: #333333;
        color: #ffffff;
        border: 1px solid #555555;
    }
    .stButton button {
        border-radius: 25px;
        padding: 10px 25px;
        background-color: #ff9800;
        color: white;
        border: none;
    }
    .stButton button:hover {
        background-color: #e68900;
    }
    </style>
""", unsafe_allow_html=True)

def initialize_files():
    """Create CSV files with headers if they don't exist"""
    if not os.path.exists("contacts.csv"):
        with open("contacts.csv", "w") as f:
            f.write("Name,Phone,Email,Address\n")
    if not os.path.exists("tasks.csv"):
        with open("tasks.csv", "w") as f:
            f.write("Title,Description,DueDate,Status,AssignedTo\n")

def process_command(command):
    """Process natural language command through backend"""
    try:
        response = master_process_command(command)
        return response
    except Exception as e:
        return {"result": {"status": "error", "message": str(e)}}

def chat_interface():
    """Main chat interface"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(
                    f'<div class="chat-message user-message">👤 {message["content"]}</div>', 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="chat-message bot-message">🤖 {message["content"]}</div>', 
                    unsafe_allow_html=True
                )
    
    # Input area
    with st.form("chat-form", clear_on_submit=True):
        user_input = st.text_input(
            "Your command:", 
            placeholder="Try: 'Add contact John' or 'Mark task as completed'",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Send")
    
    if submitted and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.spinner("Processing..."):
            response = process_command(user_input)
            formatted_response = f"""
            **Result:**
            ```json
            {json.dumps(response['result'], indent=2)}
            ```
            """
        
        st.session_state.messages.append({"role": "assistant", "content": formatted_response})
        st.rerun()

def sidebar_help():
    """Help sidebar with examples"""
    with st.sidebar:
        st.header("📌 Command Examples")
        st.markdown("""
        **Contacts:**
        - `add contact "John Doe" phone=1234567890 email=john@example.com`
        - `edit contact where email=john@example.com set name="John Smith"`
        - `view contacts where phone=1234567890`
        - `delete contact where name="John Doe"`

        **Tasks:**
        - `add task "Finish report" due=tomorrow assigned_to=John`
        - `mark task "Finish report" as completed`
        - `view all tasks sorted by due_date`
        - `delete task "Old project"`
        """)
        if st.button("Clear Chat History"):
            st.session_state.messages = []

def main():
    initialize_files()
    st.title("🤖 Personal Assistant")
    st.caption("Your AI-powered assistant for managing contacts and tasks")
    
    sidebar_help()
    chat_interface()

if __name__ == "__main__":
    main()
