import re
import logging

# Configure logging
logging.basicConfig(
    filename='langchainscrape.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def strip_markdown(text):
    """
    Removes Markdown formatting from the given text.

    Args:
        text (str): The text containing Markdown syntax.

    Returns:
        str: The plain text without Markdown.
    """
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`.*?`', '', text)
    # Remove images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links but keep the link text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold and italics
    text = re.sub(r'(\*\*|\*|__|_)', '', text)
    # Remove headers
    text = re.sub(r'^#+\s', '', text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r'^>\s', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    # Remove unordered list markers
    text = re.sub(r'^[-\*\+]\s+', '', text, flags=re.MULTILINE)
    # Remove ordered list numbers
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove remaining Markdown symbols
    text = re.sub(r'[<>]', '', text)
    return text.strip()

def log_info(message):
    """
    Logs an informational message.

    Args:
        message (str): The message to log.
    """
    logging.info(message)

def log_error(message):
    """
    Logs an error message.

    Args:
        message (str): The message to log.
    """
    logging.error(message)
