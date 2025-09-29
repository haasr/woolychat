"""
Utility modules for WoolyChat application
"""

from .file_manager import FileManager
from .conversation_manager import ConversationManager
from .text_extractor import TextExtractor

import socket

def get_available_port(start_port):
    """
    Attempts to find an available port to run the Flask app.
    
    Args:
        start_port (int): The starting port number to check
    
    Returns:
        int: The first available port number
    """

    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Attempt to bind the socket to an address and the desired port
        sock.bind(('0.0.0.0', start_port))
        sock.close()

        # If the above line doesn't raise an exception, it means the port is available
        return start_port
    
    except socket.error:
        # The port is in use. Try the next port by incrementing start_port
        return get_available_port(start_port + 1)

__all__ = ['FileManager', 'ConversationManager', 'TextExtractor', 'get_available_port']