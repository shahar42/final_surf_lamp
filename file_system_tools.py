import os

def create_directory(path: str) -> str:
    """Creates a directory if it doesn't already exist."""
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {e}"

def create_or_write_file(file_path: str, content: str) -> str:
    """Creates or overwrites a file with the given content."""
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote file: {file_path}"
    except Exception as e:
        return f"Error writing file {file_path}: {e}"

def read_document_chunk(file_path: str) -> str:
    """Reads the content of a text file (a chunk of the main document)."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Chunk file not found at {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {e}"# TODO: Add content for file_system_tools.py
