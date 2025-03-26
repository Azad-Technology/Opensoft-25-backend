# index.py
import streamlit as st
import asyncio
import uuid
import time # For debug
from chat_bot import chat_complete

# --- Initialization ---
st.set_page_config(page_title="Employee Chatbot", page_icon="💬", layout="wide")
st.title("💬 Employee Chatbot")

# Initialize session state variables if they don't exist
default_session_id = str(uuid.uuid4())
if "session_id" not in st.session_state:
    st.session_state.session_id = default_session_id
# if "messages" not in st.session_state: # Optional: Keep global history if needed
#     st.session_state.messages = []
if "current_messages" not in st.session_state:
    st.session_state.current_messages = []
if "employee_id" not in st.session_state:
    st.session_state.employee_id = ""
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
if "employee_id_input_key" not in st.session_state:
     st.session_state.employee_id_input_key = "emp_id_" + str(uuid.uuid4())
if "is_initializing_chat" not in st.session_state: # Flag to prevent double init
     st.session_state.is_initializing_chat = False

print(f"\n--- Script Run Start {time.time()} ---")
print(f"Session State: employee_id={st.session_state.employee_id}, active={st.session_state.conversation_active}, len(current_messages)={len(st.session_state.current_messages)}, initializing={st.session_state.is_initializing_chat}")


# --- Helper Functions ---
def reset_conversation_state(new_employee_id):
    """Resets state for a new conversation."""
    print(f"Resetting conversation state for {new_employee_id}")
    st.session_state.employee_id = new_employee_id
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.current_messages = []
    st.session_state.conversation_active = True
    st.session_state.is_initializing_chat = True # SET FLAG: We need to get the first message

# --- Sidebar ---
with st.sidebar:
    st.header("Conversation Control")
    employee_id_input = st.text_input(
        "Enter Employee ID:",
        key=st.session_state.employee_id_input_key,
        value=st.session_state.get(st.session_state.employee_id_input_key, ""),
        help="Enter the Employee ID and click 'Start Chat'"
    )

    if st.button("🚀 Start Chat", use_container_width=True):
        print("Start Chat button clicked")
        if employee_id_input:
            if (st.session_state.employee_id != employee_id_input or
                    not st.session_state.conversation_active):
                reset_conversation_state(employee_id_input)
                print("Triggering rerun after reset")
                st.rerun() # Rerun to trigger the initialization logic below
            # No need for the 'elif' case, clicking again on active chat is now harmless
        else:
            st.warning("Please enter an Employee ID.", icon="⚠️")
            print("Start Chat clicked without Employee ID.")

    st.divider()
    st.caption(f"Active Employee: {st.session_state.employee_id if st.session_state.employee_id else 'None'}")
    st.caption(f"Session ID: {st.session_state.session_id}")
    st.caption(f"Status: {'Active' if st.session_state.conversation_active else 'Inactive'}")

# --- Main Chat Area ---
print("Displaying current messages...")
# Display messages first
for message in st.session_state.current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
print(f"Displayed {len(st.session_state.current_messages)} messages.")


# --- Chat Logic ---
print(f"Checking chat logic condition: employee_id='{st.session_state.employee_id}', active={st.session_state.conversation_active}")
if st.session_state.employee_id and st.session_state.conversation_active:

    # 1. Handle Initial Bot Message ONLY if the flag is set
    print(f"Checking initial message condition: initializing={st.session_state.is_initializing_chat}")
    if st.session_state.is_initializing_chat:
        print(f"--- Getting Initial Bot Message {time.time()} ---")
        # Ensure messages are still empty, just in case.
        if not st.session_state.current_messages:
            with st.spinner("Initiating conversation..."):
                try:
                    print(f"Calling asyncio.run(chat_complete) for initial message...")
                    response = asyncio.run(
                        chat_complete(
                            st.session_state.employee_id,
                            st.session_state.session_id
                        )
                    )
                    print(f"asyncio.run(chat_complete) for initial message DONE.")

                    if "error" in response:
                        st.error(f"Error starting conversation: {response['error']}", icon="🚨")
                        st.session_state.conversation_active = False # Stop conversation
                        st.session_state.is_initializing_chat = False # Reset flag on error
                        print(f"Error in initial message: {response['error']}")
                        st.rerun() # Rerun to show error and update state
                    else:
                        assistant_msg = {"role": "assistant", "content": response["response"]}
                        st.session_state.current_messages.append(assistant_msg)
                        st.session_state.is_initializing_chat = False # CLEAR FLAG: Initialization done
                        print(f"Initial message added. Clearing flag. Triggering rerun.")
                        st.rerun() # Rerun to display the new message

                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}", icon="🔥")
                    st.session_state.conversation_active = False
                    st.session_state.is_initializing_chat = False # Reset flag on exception
                    print(f"EXCEPTION during initial message fetch: {e}")
                    st.rerun() # Rerun to show error and update state
        else:
             # Messages already exist, shouldn't happen if logic is right, but reset flag just in case.
             print("WARNING: is_initializing_chat was true, but messages already exist. Resetting flag.")
             st.session_state.is_initializing_chat = False
        print(f"--- Finished Initial Bot Message Block {time.time()} ---")


    # 2. Handle User Input and Bot Response (only if not initializing)
    elif not st.session_state.is_initializing_chat: # Make sure init is finished
        print("Setting up chat input...")
        user_input = st.chat_input("Your response...", disabled=not st.session_state.conversation_active)
        print(f"Chat input value: {'Set' if user_input else 'None'}")

        if user_input:
            print(f"--- Processing User Input {time.time()} ---")
            # Add and display user message immediately
            user_msg = {"role": "user", "content": user_input}
            st.session_state.current_messages.append(user_msg)
            # Display happens on the *next* rerun because of the structure
            # To display immediately, uncomment below, but it might flash
            # with st.chat_message("user"):
            #    st.markdown(user_input)
            print("User message added to state.")


            # Get and display bot response
            with st.spinner("Thinking..."):
                try:
                    print(f"Calling asyncio.run(chat_complete) for user input...")
                    response = asyncio.run(
                        chat_complete(
                            st.session_state.employee_id,
                            st.session_state.session_id,
                            user_input
                        )
                    )
                    print(f"asyncio.run(chat_complete) for user input DONE.")

                    if "error" in response:
                        st.error(f"Error getting response: {response['error']}", icon="🚨")
                        print(f"Error in bot response: {response['error']}")
                        # Let the error show, don't rerun automatically? Or rerun?
                        # Consider if you want the user message removed on error
                    else:
                        assistant_msg = {"role": "assistant", "content": response["response"]}
                        st.session_state.current_messages.append(assistant_msg)
                        print("Assistant response added to state.")

                        if response.get("conversation_status") == "complete":
                            st.success("Conversation complete!", icon="✅")
                            st.session_state.conversation_active = False
                            print("Conversation complete. Set active=False.")
                            # Rerun to disable input and show success
                            st.rerun()
                        else:
                             # Rerun to display the new assistant message
                             print("Conversation ongoing. Triggering rerun.")
                             st.rerun()


                except Exception as e:
                    st.error(f"An unexpected error occurred while getting response: {e}", icon="🔥")
                    print(f"EXCEPTION during bot response fetch: {e}")
                    # Maybe deactivate?
                    # st.session_state.conversation_active = False
                    # st.rerun()
            print(f"--- Finished User Input Processing Block {time.time()} ---")

else:
     print("Chat logic condition not met (No EmployeeID or Conversation Inactive).")


# --- Instructions/Status ---
if not st.session_state.employee_id:
    st.info("Please enter an Employee ID in the sidebar and click 'Start Chat'.")
elif not st.session_state.conversation_active and st.session_state.current_messages:
     # Only show 'ended' message if it wasn't just an initialization error
     if not st.session_state.is_initializing_chat:
          st.info("Conversation ended. Enter the same or a new Employee ID and click 'Start Chat' to begin again.")
