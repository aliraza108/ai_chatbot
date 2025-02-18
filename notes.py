from llama_index.core.tools import FunctionTool
import os

note_file = os.path.join("data", "notes.text")

def saven_note(note):
    if not os.path.exists(note_file):
        open(note_file,"w")
    
    with open(note_file, "a") as f:
        f.writelines([note + "\n"])
    
    return "saved note"

note_engine = FunctionTool.from_defaults(
    fn=saven_note,
    name="note_saver",
    description="this is a tool for saving note in a filse for user"
)