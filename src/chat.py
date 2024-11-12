# src/chat.py

import os
from dotenv import load_dotenv
from groq import Groq  # Import the Groq client for chat completions
from embedding import EmbeddingStore
from utils import strip_markdown, log_info, log_error
import json

# Load environment variables from .env file
load_dotenv()
groq_api_key = os.getenv('GROQ_API_KEY')  # Groq API key

# Initialize the Groq client
groq_client = Groq(api_key=groq_api_key)

# Initialize the conversation history
conversation_history = []

# Initialize the embedding store
embedding_store = EmbeddingStore()

# Define maximum tokens allowed per request (adjust based on Groq's documentation)
MAX_TOKENS_PER_REQUEST = 4096  # Example limit; replace with actual if different

# Path to current_relevant_context.txt
CURRENT_CONTEXT_FILE = "current_relevant_context.txt"

def initialize_conversation():
    """
    Initializes the conversation with a system message defining the bot's purpose.
    """
    system_message = {
        'role': 'system',
        'content': (
            "You are a helpful assistant designed to provide information exclusively from credible "
            "Hawaii government websites. Your responses should be accurate, concise, and strictly focused "
            "on topics related to Hawaii government information. Do not provide information outside this scope."
            "Your name is Koa and you are designed to be as helpful as possible. Do not say anything about 'based on provided context' "
            "Simply use the context and provide your final answer to the user."
        )
    }
    conversation_history.append(system_message)
    log_info("Initialized conversation with system message.")

def get_relevant_context(user_query: str, top_k: int = 3, max_chunk_size: int = 500) -> str:
    """
    Retrieves relevant context from the embedding store based on the user's query.

    Args:
        user_query (str): The user's search query.
        top_k (int): Number of top relevant contexts to retrieve.
        max_chunk_size (int): Maximum number of words per chunk.

    Returns:
        str: The concatenated relevant context with citations.
    """
    results = embedding_store.search(user_query, top_k)
    context = ""
    total_length = 0  # To keep track of the total length

    for source, similarity in results:
        file_path = os.path.join("Scraped Data", source)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Extract source URL and content
                if len(lines) >= 3:
                    source_url = lines[0].strip()
                    content = ''.join(lines[2:]).strip()
                else:
                    source_url = "Unknown Source"
                    content = ''.join(lines[1:]).strip() if len(lines) > 1 else ''.join(lines).strip()

                # Chunk the text
                words = content.split()
                for i in range(0, len(words), max_chunk_size):
                    chunk = ' '.join(words[i:i + max_chunk_size])
                    summarized_chunk = summarize_text(chunk)
                    chunk_with_citation = f"From {source} ({source_url}):\n{summarized_chunk}\n\n"
                    chunk_length = len(chunk_with_citation)

                    if total_length + chunk_length > MAX_TOKENS_PER_REQUEST * 4:  # Approximate character to token ratio
                        break  # Stop adding more context to avoid exceeding the limit

                    context += chunk_with_citation
                    total_length += chunk_length

    # Write the current context to current_relevant_context.txt
    with open(CURRENT_CONTEXT_FILE, 'w', encoding='utf-8') as ctx_file:
        ctx_file.write(context)
    log_info(f"Updated {CURRENT_CONTEXT_FILE} with the latest context.")

    return context

def summarize_text(text: str, max_length: int = 500) -> str:
    """
    Summarizes the given text to a maximum length.

    Args:
        text (str): The text to summarize.
        max_length (int): The maximum number of characters in the summary.

    Returns:
        str: The summarized text.
    """
    if len(text) <= max_length:
        return text
    else:
        # Simple truncation; replace with actual summarization if desired
        return text[:max_length] + "..."

def manage_conversation_history(new_message: dict, max_history: int = 10):
    """
    Manages the conversation history by maintaining a maximum number of messages.

    Args:
        new_message (dict): The new message to add.
        max_history (int): Maximum number of messages to retain.
    """
    conversation_history.append(new_message)
    if len(conversation_history) > max_history + 1:  # +1 to account for the initial system message
        # Remove the oldest message (after the system messages)
        conversation_history.pop(1)

def get_groq_response(user_input: str) -> str:
    """
    Sends the user's input along with relevant context to the Groq API and retrieves the bot's response.

    Args:
        user_input (str): The message input by the user.

    Returns:
        str: The response from the bot or an error message.
    """
    # If conversation history is empty, initialize it with system message
    if not conversation_history:
        initialize_conversation()

    # Retrieve relevant context
    context = get_relevant_context(user_input)

    # Append context to conversation history as a system message
    if context:
        system_context_message = {'role': 'system', 'content': context}
        manage_conversation_history(system_context_message)

    # Append user input to conversation history
    user_message = {'role': 'user', 'content': user_input}
    manage_conversation_history(user_message)

    try:
        response = groq_client.chat.completions.create(
            messages=conversation_history,
            model='llama3-70b-8192'  # Replace with the model version you’re using
        )
        bot_response = response.choices[0].message.content.strip()
        # Strip Markdown from the bot's response
        bot_response = strip_markdown(bot_response)
        # Append assistant response to conversation history
        assistant_message = {'role': 'assistant', 'content': bot_response}
        manage_conversation_history(assistant_message)
        return bot_response
    except Exception as ex:
        log_error(f"An error occurred: {ex}")
        return "Error: Unable to retrieve response."
