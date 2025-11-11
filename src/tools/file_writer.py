import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from .base import BaseTool
from ..utils import get_logger , config

logger = get_logger(__name__)


class FileWriterTool(BaseTool):
    """
    Write text content to local files.
    
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize file writer tool.
        
        Args:
            output_dir: Directory where files will be written
                If None, uses config.INFO_INSERTS_DIR

        """
        self.output_dir = output_dir or config.INFO_INSERTS_DIR
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FileWriterTool initialized: output_dir={self.output_dir}")
    
    @property
    def name(self) -> str:
        return "file_writer"
    
    @property
    def description(self) -> str:
        return """Write text content to a local file. Use this tool when:
- User asks to save/export content to a file
- Creating summaries or reports to save
- Exporting search results, chat content, or any text

this tool returns the filepath.
if user didn't provide a filename you provide clear short name according to the content.
"""
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": """Name of the file to create."""
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file. Can be multi-line. "
                }

            },
            "required": ["filename", "content"]
        }
    
    def execute(
        self,
        filename: str,
        content: str,
        format: str = "plain",
    ) -> str:
        """
        Write content to a file.
        
        Args:
            filename: Name of file to create
            content: Text content to write
            format: Output format ('plain' or 'markdown')
        
        Returns:
            Success message with file path

        """
        if not filename.strip():
            return "Error: Filename cannot be empty"
        
        if not content.strip():
            return "Error: Content cannot be empty"
        
        try:
     
            # Ensure .txt extension
            if not filename.lower().endswith('.txt'):
                filename += '.txt'
            
            filename.replace(" ","_")
            filename = filename.lower()
            
            # Full path
            file_path = self.output_dir / filename
            
            # Add time stamp 
            formatted_content = self._format_content(content)
            
            # Write to file
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            # Log success
            logger.info(f"File written: {file_path} ({len(formatted_content)} chars.")
            
            # Return success message
            return f"Created file: {file_path}\n\nFile contains {len(formatted_content)} characters."
        
        except Exception as e:
            error_msg = f"Failed to write file: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
      
    def _format_content(self, content: str) -> str:
        """
        Add creation or updating time  
        Args:
            content: Raw content 
        Returns:
            Formatted content
        """
        header = f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'-' * 60}\n\n"
        return header + content
    
    def list_files(self) -> list:
        """
        List all files in the output directory.
        
        Returns:
            List of filenames
        """
        try:
            files = [f.name for f in self.output_dir.iterdir() if f.is_file()]
            return sorted(files)
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def read_file(self, filename: str) -> str:
        """
        Read a file from the output directory.
        
        Args:
            filename: Name of file to read
        
        Returns:
            File contents or error message
        
        Why this method?
        - User might ask "what's in file X?"
        - LLM can retrieve previously saved content
        - Useful for follow-up queries
        """
        try:
            if not filename.lower().endswith('.txt'):
                filename += '.txt'

            filename.replace(" ","_")
            filename = filename.lower()
            file_path = self.output_dir / filename  
            
            if not file_path.exists():
                return f"""Error: File '{filename}' not found . files avaliable are : {self.list_files}
if any name is similar ask user if he meant the similar name

"""
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"File read: {file_path} ({len(content)} chars)")
            return content
        
        except Exception as e:
            error_msg = f"Failed to read file: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

