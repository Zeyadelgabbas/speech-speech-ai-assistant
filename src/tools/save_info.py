from typing import Dict , Any , List 
from datetime import datetime
from ..utils import config , get_logger 
from .base import BaseTool

logging = get_logger(__name__)


class SaveInfoTool(BaseTool):

    """ Saves quick personal notes and calender"""

    def __init__(self):

        self.notes_file = config.USER_NOTES_FILE
        self.notes_file.parent.mkdir(parents=True , exist_ok=True)

        if not self.notes_file.exists():
            self._create_notes_file()


    def _create_notes_file(self) -> None:
        """ creates the user notes file with default content"""

        self.header = """# Personal Notes & Reminders

        This file stores quick notes , reminders and personal information.
        each entry is timestamped automatically.

        -------------------------------------------------------
        
        """

        self.footer = """

Add Below any information you want AI to remember (Don't delete this line and dont add '[' to the start of a line):

1-
2-
3-
4-
"""
        full_page = self.header + self.footer

        with open (self.notes_file,'w',encoding='utf-8') as f:
            f.write(full_page)
        logging.info("Created default user_notes.txt")

        return
    
    @property
    def name(self):
        return "save_read_information"
    
    @property
    def description(self):
        return """ Save and retreive quick personal notes , reminders to user's notes file . 
        Use for reading or saving : Notes , meetings , reminders , appointments , calender . 
        Not for : exporting content (use file_writer tool).
        """

    @property 
    def parameters_schema(self) -> Dict[str,Any]:
        return {
            'type':'object',
            'properties': {
                "content" : {
                    "type":"string",
                    "description":"Information to keep when mode = 'append'. be concise and informative. ignore if mode is 'read'"
                },
                "mode":{
                    "type":"string",
                    "enum":["read","append"],
                    "description": "Choose 'append' to save new note , 'read' to retrieve notes"
                },
                "limit":{
                    "type":"string",
                    "description":"retreive last N  notes (eg., 8) or 'all' to retrieve all notes",
                    "default": "all"
                }
            },
            'required':['mode']
        }
    

    def execute(self , mode: str , content: str=None , limit : str = 'all' )-> str:

        """ Writes the information content in user's note's info """

        try:
            if not self.notes_file.exists():
                logging.error("notes file doesnt exist")
                self._create_notes_file()
                return "Error : notes file doesn't exist. File is now created but empty"
            if mode == 'append':
                result = self._append_to_notes(content)

                return result
                
            elif mode =='read':
                result = self._read_from_notes(limit = limit)
                return result
            else:
                return "Error: invalid mode"
            
        except Exception as e: 
            error_msg = f"Failed to {mode} info error : {str(e)}"
            logging.error(error_msg)
            return f"Error : {error_msg}"

    def _append_to_notes(self,content: str):

        """ appends notes to the user's note file"""

        if not content.strip():
            logging.error(f"Content is empty for saving tool")
            return "Error : content is empty"
        
        try:

            timestampt = datetime.now().strftime("%Y-%m-%d  %H:%M")
            content = f"[{timestampt}] : {content.strip()}\n\n"

            manual_idx, lines, _ = self._check_for_manual_info()
            if manual_idx is not None and lines:
                lines.insert(manual_idx,'\n'+content)

            else:
                lines.append('\n'+content)

            with open(self.notes_file,'w',encoding='utf-8') as f:
                f.writelines(lines)
        
            return "content appended to notes successfully "
        except Exception as e: 
            error_msg = f"Failed to save notes : {str(e)}"
            logging.error(error_msg)
            return f"Error : {error_msg}"

    def _check_for_manual_info(self) :
        """ returns the manual inserted informations and notes """
        with open(self.notes_file,'r',encoding='utf-8') as f:
            lines = f.readlines()

        start_indices = []
        for i, line in enumerate(lines): 
            if line.strip().lower().startswith('add below any information you want'):
                return i , lines , start_indices
            elif line.strip().startswith('['):
                start_indices.append(i)

            
        return None , lines , start_indices

    def _read_from_notes(self, limit: str = 'all'):

        # read all lines
        manual_idx , lines , start_indices = self._check_for_manual_info()
        is_manual = False
        if manual_idx is not None:
            is_manual = True
            manual_content = lines[manual_idx:]
            lines = lines[:manual_idx]
        
        if not start_indices and not is_manual:
            return "No notes found yet in your notes file."
        notes = []
        for i , start_idx in enumerate(start_indices):
            end_idx = start_indices[i+1] if i+1 <len(start_indices) else len(lines)
            note = ''.join(lines[start_idx:end_idx])

            notes.append(note)

        if limit !='all':
            try:
                notes = notes[-int(limit):]
            except Exception as e: 
                logging.error(f"limit must be an integer  Error : {e}")
                return "Invalid limit value must be an integer or 'all'."

        if is_manual:
            notes.extend(manual_content)

        return "User's notes file content : \n\n" + '\n\n'.join(notes)
        
