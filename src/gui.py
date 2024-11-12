# src/gui.py

import customtkinter as ct
import threading
import time
from chat import get_groq_response
from utils import strip_markdown, log_info, log_error
import re
import webbrowser
import random

def open_url(url):
    """
    Opens the given URL in the default web browser.
    """
    webbrowser.open(url)

class TypingIndicator:
    def __init__(self, parent_frame, main_window):
        """
        Initializes the typing indicator.

        Args:
            parent_frame (CTkScrollableFrame): The frame where the typing indicator will be displayed.
            main_window (CTk): The main application window used to schedule updates.
        """
        self.parent_frame = parent_frame
        self.main_window = main_window
        self.bubble_frame = ct.CTkFrame(parent_frame, fg_color="#E5E5EA", corner_radius=15)
        self.bubble_frame.pack(anchor="w", pady=5, padx=10)

        self.label = ct.CTkLabel(
            self.bubble_frame,
            text="Bot is typing.",
            text_color="#000000",
            wraplength=600,  # Increased from 250 to 300
            justify="left"
        )
        self.label.pack(pady=5, padx=10)

        self.dots = 1
        self.after_id = None
        self.start_time = time.time()  # Record the start time
        self.start_animation()

    def start_animation(self):
        """Starts the typing animation by scheduling the first update."""
        self.update_text()

    def update_text(self):
        """Updates the label text to simulate typing by cycling dots."""
        self.label.configure(text="Bot is typing" + "." * self.dots)
        self.dots = (self.dots % 3) + 1  # Cycle dots between 1 and 3
        # Schedule the next update after 500 milliseconds using the main window
        self.after_id = self.main_window.after(500, self.update_text)

    def get_elapsed_time(self):
        """Returns the elapsed time since the typing indicator was shown."""
        return time.time() - self.start_time

    def stop(self):
        """Stops the typing animation and removes the typing indicator from the UI."""
        if self.after_id:
            self.main_window.after_cancel(self.after_id)
        self.bubble_frame.destroy()

def display_message(chat_frame, sender, message):
    """
    Displays a message in the chat frame.

    Args:
        chat_frame (CTkScrollableFrame): The chat display frame.
        sender (str): The sender of the message ("user" or "assistant").
        message (str): The message content.
    """
    bubble_color = "#e5e3d9" if sender == "user" else "#E5E5EA"
    text_color = "#000000"
    alignment = "e" if sender == "user" else "w"

    # Message bubble frame
    bubble_frame = ct.CTkFrame(chat_frame, fg_color=bubble_color, corner_radius=15)
    bubble_frame.pack(anchor=alignment, pady=5, padx=10)

    # Parse the message for URLs
    url_pattern = re.compile(r'(https?://\S+)')
    parts = url_pattern.split(message)

    for part in parts:
        if re.match(url_pattern, part):
            # It's a URL, create a clickable button
            link_button = ct.CTkButton(
                bubble_frame,
                text=part,
                fg_color="#FFFFFF",
                hover_color="#DDDDDD",
                text_color="#1a73e8",
                border_width=0,
                corner_radius=5,
                command=lambda url=part: open_url(url)
            )
            link_button.pack(anchor="w", pady=2, padx=10)
        else:
            # Regular text
            if part.strip() != "":
                label = ct.CTkLabel(
                    bubble_frame,
                    text=part,
                    text_color=text_color,
                    wraplength=300,  # Ensure the bubble doesn't stretch too wide
                    justify="left"
                )
                label.pack(anchor="w", pady=2, padx=10)


def process_input(user_entry, chat_frame, window, typing_indicator_ref):
    """
    Processes the user's input by displaying it and fetching the bot's response.

    Args:
        user_entry (CTkEntry): The user input entry widget.
        chat_frame (CTkScrollableFrame): The chat display frame.
        window (CTk): The main application window.
        typing_indicator_ref (dict): A dictionary to hold the typing indicator reference.
    """
    user_input = user_entry.get().strip()
    if user_input:
        display_message(chat_frame, "user", user_input)
        user_entry.delete(0, ct.END)

        # Display the typing indicator
        typing_indicator_ref['indicator'] = TypingIndicator(chat_frame, window)

        # Fetch and display the bot response in a separate thread to avoid freezing the GUI
        def fetch_and_display_response():
            response = get_groq_response(user_input)
            if typing_indicator_ref['indicator']:
                elapsed_time = typing_indicator_ref['indicator'].get_elapsed_time()
                minimum_duration = 1.0  # Minimum duration in seconds
                remaining_time = minimum_duration - elapsed_time
                if remaining_time > 0:
                    # Schedule display_bot_response after the remaining time
                    window.after(int(remaining_time * 1000), lambda: display_bot_response(response, typing_indicator_ref, chat_frame))
                else:
                    # Schedule display_bot_response immediately
                    window.after(0, lambda: display_bot_response(response, typing_indicator_ref, chat_frame))

        threading.Thread(target=fetch_and_display_response, daemon=True).start()

def display_bot_response(response, typing_indicator_ref, chat_frame):
    """
    Displays the bot's response and removes the typing indicator.

    Args:
        response (str): The bot's response message.
        typing_indicator_ref (dict): A dictionary holding the typing indicator reference.
        chat_frame (CTkScrollableFrame): The chat display frame.
    """
    if typing_indicator_ref.get('indicator'):
        typing_indicator_ref['indicator'].stop()
        typing_indicator_ref['indicator'] = None
    display_message(chat_frame, "assistant", response)
    # Scroll to the bottom
    scroll_to_bottom(chat_frame)

def scroll_to_bottom(chat_frame):
    """
    Scrolls the chat frame to the bottom.

    Args:
        chat_frame (CTkScrollableFrame): The chat display frame.
    """
    try:
        # Access the underlying Tkinter Canvas
        for child in chat_frame.winfo_children():
            if isinstance(child, ct.CTkCanvas):
                child.yview_moveto(1.0)
                break
    except Exception as e:
        log_error(f"Failed to scroll to bottom: {e}")

def create_gui():
    """
    Creates and runs the GUI application.
    """
    ct.set_appearance_mode("Light")  # or "Dark" for dark mode
    ct.set_default_color_theme("blue")  # "blue" is the default theme

    # Main window setup
    window = ct.CTk()
    window.geometry("600x800")
    window.title("Koa - Hawaiʻi Government Assistant")

    # Chat display frame
    chat_frame = ct.CTkScrollableFrame(window, fg_color="#FFFFFF")
    chat_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Randomized introduction message
    intro_messages = [
        "Aloha! I'm Koa, here to provide you with accurate and helpful information from trusted Hawaiʻi government sources. How can I assist you today?",
        "Hi! I'm Koa, your go-to assistant for Hawaiʻi government information. Feel free to ask me anything related to local policies, services, or resources!",
        "Welcome! I'm Koa, here to help with any Hawaiʻi government-related questions. Let me know how I can assist you!",
        "Aloha! I'm Koa, ready to share trusted Hawaiʻi government information with you. What would you like to know today?",
        "Hello! I’m Koa, your assistant for all things related to Hawaiʻi government. I’m here to make finding the information you need as simple as possible. How can I help?"
    ]
    display_message(chat_frame, "assistant", random.choice(intro_messages))

    # User input frame at the bottom
    input_frame = ct.CTkFrame(window)
    input_frame.pack(fill="x", pady=10, padx=10)

    user_entry = ct.CTkEntry(input_frame, placeholder_text="Type a message...", width=480)
    user_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)

    # Updated Send Button with matching color
    send_button = ct.CTkButton(
        input_frame,
        text="Send",
        command=lambda: process_input(user_entry, chat_frame, window, typing_indicator_ref),
        fg_color="#e5e3d9",        # Set to match user message bubble color
        hover_color="#d4d1c6",      # Optional: a slightly darker shade on hover
        text_color="#000000",       # Ensure text is readable on light background
        corner_radius=15            # Match the corner radius of message bubbles
    )
    send_button.pack(side="right")

    # Dictionary to hold typing indicator reference
    typing_indicator_ref = {'indicator': None}

    # Bind the Enter key to send message
    def on_enter_press(event):
        process_input(user_entry, chat_frame, window, typing_indicator_ref)

    user_entry.bind("<Return>", on_enter_press)

    # Run the app
    window.mainloop()

if __name__ == "__main__":
    create_gui()
