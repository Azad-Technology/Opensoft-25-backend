import traceback  # Import traceback for better error logging
import uuid

import gradio as gr

# Make sure this import path is correct for your project structure
from src.chatbot.chat_bot import chat_complete


# Keep chat_with_bot async as it calls await chat_complete
async def chat_with_bot(employee_id: str, message: str, session_id: str, history: list):
    """Handles both starting a chat and submitting messages."""
    print("--- chat_with_bot called ---")  # Debug print
    print(
        f"Employee ID: {employee_id}, Session ID: {session_id}, Message: '{message}'"
    )  # Debug print

    # Initialize intent_data for return in case of early exit
    intent_data_to_display = None

    if not employee_id:
        return (
            history,
            session_id,
            "Please enter an Employee ID",
            intent_data_to_display,
        )  # Return 4 values

    if not session_id:
        session_id = str(uuid.uuid4())
        history = []  # Ensure history is cleared for a truly new session start
        print(f"Generated new Session ID: {session_id}")  # Debug print

    is_initial_call = not message

    try:
        print(
            f"Calling chat_complete (Initial Call: {is_initial_call})..."
        )  # Debug print
        response = await chat_complete(
            employee_id=employee_id,
            session_id=session_id,
            message=message
            if not is_initial_call
            else None,  # Pass None for initial call
        )
        print(f"chat_complete response: {response}")  # Debug print

        if response is None:
            history.append(
                (
                    message if message else None,
                    "Error: Received None response from backend.",
                )
            )
            # Return 4 values, intent_data is None here
            return (
                history,
                session_id,
                "An error occurred (None response)",
                intent_data_to_display,
            )

        # --- Extract intent_data if available ---
        # Use .get() to safely access intent_data, default to None if missing
        intent_data_to_display = response.get("intent_data", None)
        # -----------------------------------------

        if "error" in response:
            history.append(
                (message if not is_initial_call else None, response["error"])
            )
            # Return 4 values, intent_data might be None or potentially stale if error happened later
            return (
                history,
                session_id,
                f"An error occurred: {response['error']}",
                intent_data_to_display,
            )

        bot_message = response.get("response", "Error: Missing 'response' key.")
        conversation_status = response.get("conversation_status", "unknown")

        if not is_initial_call:
            history.append((message, None))
        history.append((None, bot_message))

        status_message = ""
        if conversation_status == "complete":
            status_message = "Conversation completed. You can start a new session."

        print(
            f"Returning history (len={len(history)}), session_id, status: '{status_message}'"
        )  # Debug print
        # Return 4 values including the extracted intent_data
        return history, session_id, status_message, intent_data_to_display

    except Exception as e:
        print(f"!!! Exception in chat_with_bot: {e!s} !!!")  # Debug print
        traceback.print_exc()  # Print full traceback for debugging
        history.append((message if not is_initial_call else None, f"Error: {e!s}"))
        # Return 4 values, intent_data is None as error occurred
        return history, session_id, f"An unexpected error occurred: {e!s}", None


# Function to handle the "Start Chat" button click - NO CHANGE NEEDED HERE
# It calls chat_with_bot which now returns 4 values, the click handler handles outputs
async def start_chat_handler(employee_id: str, current_history: list):
    """Initiates a new chat session, getting the first bot message."""
    print("--- start_chat_handler called ---")  # Debug print
    new_session_id = str(uuid.uuid4())
    return await chat_with_bot(
        employee_id, "", new_session_id, []
    )  # Pass empty history


# Function to handle the "New Session" button click (remains synchronous)
def start_new_session():
    """Resets the UI for a new session."""
    print("--- start_new_session called ---")  # Debug print
    new_session_id = str(uuid.uuid4())
    # Return empty history, new session ID, empty status, interactive message box, AND None for intent data
    return (
        [],
        new_session_id,
        "",
        gr.Textbox(value="", label="Message", interactive=True),
        None,
    )  # Return 5 values


def create_chatbot_interface():
    with gr.Blocks() as demo:
        gr.Markdown("## Employee Chatbot")

        with gr.Row():
            employee_id = gr.Textbox(label="Employee ID")
            session_id = gr.Textbox(
                label="Session ID", value=str(uuid.uuid4()), interactive=False
            )

        chatbot = gr.Chatbot(label="Conversation")
        msg = gr.Textbox(
            label="Message", placeholder="Type your message here...", interactive=True
        )
        status = gr.Textbox(label="Status", interactive=False)

        with gr.Row():
            submit_btn = gr.Button("Submit")
            new_session_btn = gr.Button("New Session")
            # Removed start_chat_btn based on your provided code,
            # assuming first interaction is now via Submit or Enter
            # start_chat_btn = gr.Button("Start Chat")

        # --- Add the JSON display component ---
        intent_display = gr.JSON(label="Intent Data")
        # --------------------------------------

        # --- Event Handlers ---

        # If you still need a "Start Chat" button, uncomment this and add the button back
        # start_chat_btn.click(
        #     fn=start_chat_handler,
        #     inputs=[employee_id, chatbot],
        #     outputs=[chatbot, session_id, status, intent_display] # Add intent_display to outputs
        # )

        # Submit message -> Calls chat_with_bot directly
        submit_event = submit_btn.click(
            fn=chat_with_bot,
            inputs=[employee_id, msg, session_id, chatbot],
            # --- Update outputs to include intent_display ---
            outputs=[chatbot, session_id, status, intent_display],
            # -----------------------------------------------
            api_name="submit",
        )
        submit_event.then(fn=lambda: gr.Textbox(value=""), outputs=msg)

        # Submit on Enter key press in the message box
        msg.submit(
            fn=chat_with_bot,
            inputs=[employee_id, msg, session_id, chatbot],
            # --- Update outputs to include intent_display ---
            outputs=[chatbot, session_id, status, intent_display],
            # -----------------------------------------------
        ).then(fn=lambda: gr.Textbox(value=""), outputs=msg)

        # Start new session -> Calls start_new_session
        new_session_btn.click(
            fn=start_new_session,
            inputs=[],
            # --- Update outputs to include intent_display ---
            outputs=[chatbot, session_id, status, msg, intent_display],
            # ------------------------------------------------
            api_name="new_session",
        )

    return demo


demo = create_chatbot_interface()  # You already have this instance

if __name__ == "__main__":
    # Make sure this instance is created before launching if not already done

    print("Launching Gradio interface...")
    demo.launch()
    print("Gradio interface launched.")
