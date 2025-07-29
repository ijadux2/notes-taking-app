#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from getpass import getpass
import argparse
import pytz
from colorama import Fore, Back, Style, init
from cryptography.fernet import Fernet
import dropbox  # pip install dropbox
import markdown  # pip install markdown

# Initialize colorama
init(autoreset=True)

# Constants
NOTES_FILE = "notes.json"
CONFIG_FILE = "config.json"
KEY_FILE = ".key"

class NoteTakerPro:
    def __init__(self):
        self.notes = []
        self.config = {
            'encrypted': False,
            'cloud_sync': False,
            'dropbox_token': None,
            'timezone': 'UTC'
        }
        self.load_config()
        self.setup_encryption()
        self.load_notes()
        self.dbx = None
        if self.config['cloud_sync']:
            self.setup_dropbox()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config.update(json.load(f))
    
    def save_config(self):
        """Save configuration to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_encryption(self):
        """Setup encryption key"""
        if not self.config['encrypted']:
            return
            
        if not os.path.exists(KEY_FILE):
            key = Fernet.generate_key()
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
        else:
            with open(KEY_FILE, 'rb') as f:
                key = f.read()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data):
        """Encrypt data"""
        if not self.config['encrypted']:
            return data
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, data):
        """Decrypt data"""
        if not self.config['encrypted']:
            return data
        return self.cipher.decrypt(data.encode()).decode()
    
    def setup_dropbox(self):
        """Initialize Dropbox connection"""
        if not self.config['dropbox_token']:
            print(Fore.RED + "No Dropbox token configured!")
            return
        self.dbx = dropbox.Dropbox(self.config['dropbox_token'])
    
    def sync_to_cloud(self):
        """Sync notes to Dropbox"""
        if not self.dbx:
            return
        try:
            with open(NOTES_FILE, 'rb') as f:
                self.dbx.files_upload(f.read(), f'/{NOTES_FILE}', mode=dropbox.files.WriteMode.overwrite)
            print(Fore.GREEN + "Notes synced to Dropbox!")
        except Exception as e:
            print(Fore.RED + f"Sync failed: {str(e)}")
    
    def sync_from_cloud(self):
        """Sync notes from Dropbox"""
        if not self.dbx:
            return
        try:
            self.dbx.files_download_to_file(NOTES_FILE, f'/{NOTES_FILE}')
            self.load_notes()
            print(Fore.GREEN + "Notes synced from Dropbox!")
        except Exception as e:
            print(Fore.RED + f"Sync failed: {str(e)}")
    
    def load_notes(self):
        """Load notes from JSON file"""
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r') as f:
                try:
                    data = json.load(f)
                    if self.config['encrypted']:
                        self.notes = json.loads(self.decrypt(json.dumps(data)))
                    else:
                        self.notes = data
                except Exception as e:
                    print(Fore.RED + f"Error loading notes: {str(e)}")
                    self.notes = []
        else:
            self.notes = []
    
    def save_notes(self):
        """Save notes to JSON file"""
        try:
            if self.config['encrypted']:
                data = json.loads(self.encrypt(json.dumps(self.notes)))
            else:
                data = self.notes
            
            with open(NOTES_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            if self.config['cloud_sync']:
                self.sync_to_cloud()
        except Exception as e:
            print(Fore.RED + f"Error saving notes: {str(e)}")
    
    def create_note(self):
        """Create a new note"""
        print(Fore.YELLOW + "\nCREATE NEW NOTE")
        title = input(Fore.CYAN + "Title: " + Style.RESET_ALL)
        content = input(Fore.CYAN + "Content: " + Style.RESET_ALL)
        
        tags_input = input(Fore.CYAN + "Tags (comma separated): " + Style.RESET_ALL)
        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        
        reminder = None
        if input(Fore.CYAN + "Add reminder? (y/n): " + Style.RESET_ALL).lower() == 'y':
            reminder_time = input(Fore.CYAN + "Reminder time (YYYY-MM-DD HH:MM): " + Style.RESET_ALL)
            try:
                reminder = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M").isoformat()
            except ValueError:
                print(Fore.RED + "Invalid date format!")
        
        note = {
            'id': len(self.notes) + 1,
            'title': title,
            'content': content,
            'tags': tags,
            'created': datetime.now(pytz.timezone(self.config['timezone'])).isoformat(),
            'modified': datetime.now(pytz.timezone(self.config['timezone'])).isoformat(),
            'reminder': reminder
        }
        
        self.notes.append(note)
        self.save_notes()
        print(Fore.GREEN + "\nNote created successfully!")
    
    def check_reminders(self):
        """Check for due reminders"""
        now = datetime.now(pytz.timezone(self.config['timezone']))
        for note in self.notes:
            if note.get('reminder'):
                reminder_time = datetime.fromisoformat(note['reminder'])
                if now >= reminder_time:
                    print(Fore.RED + f"\nREMINDER: {note['title']} (Due: {reminder_time.strftime('%Y-%m-%d %H:%M')})")
                    print(note['content'])
                    # Optionally mark as completed
                    if input(Fore.CYAN + "Mark as completed? (y/n): " + Style.RESET_ALL).lower() == 'y':
                        note['reminder'] = None
                        self.save_notes()
    
    def export_note(self, note_id, format_type):
        """Export note to different formats"""
        note = next((n for n in self.notes if n['id'] == note_id), None)
        if not note:
            print(Fore.RED + "Note not found!")
            return
        
        filename = f"note_{note_id}_{note['title'].replace(' ', '_')}.{format_type.lower()}"
        
        if format_type == 'html':
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{note['title']}</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h1 {{ color: #333; }}
                    .meta {{ color: #666; font-size: 0.9em; }}
                    .content {{ margin-top: 20px; }}
                    .tags {{ margin-top: 20px; color: #0066cc; }}
                </style>
            </head>
            <body>
                <h1>{note['title']}</h1>
                <div class="meta">
                    Created: {note['created']}<br>
                    Modified: {note['modified']}
                </div>
                <div class="content">
                    {markdown.markdown(note['content'])}
                </div>
                <div class="tags">
                    Tags: {', '.join(note['tags'])}
                </div>
            </body>
            </html>
            """
            with open(filename, 'w') as f:
                f.write(html_content)
        elif format_type == 'md':
            md_content = f"""# {note['title']}
            
**Created:** {note['created']}  
**Modified:** {note['modified']}  

{note['content']}

**Tags:** {', '.join(note['tags'])}
            """
            with open(filename, 'w') as f:
                f.write(md_content)
        else:
            print(Fore.RED + "Unsupported format!")
            return
        
        print(Fore.GREEN + f"Note exported to {filename}")

    # The rest of the methods (list_notes, view_note, edit_note, delete_note, search_notes)
    # would be similar to the previous version but with the new fields included
    # [...] (truncated for brevity - these would be included in actual file)

    def list_notes(self):
        """List all notes"""
        if not self.notes:
            print(Fore.YELLOW + "No notes available.")
            return
        print(Fore.YELLOW + "\nALL NOTES")
        for note in self.notes:
            print(f"ID: {note['id']} | Title: {note['title']} | Tags: {', '.join(note['tags'])} | Created: {note['created']} | Modified: {note['modified']}")

    def view_note(self):
        """View a specific note"""
        try:
            note_id = int(input(Fore.CYAN + "Enter note ID to view: " + Style.RESET_ALL))
        except ValueError:
            print(Fore.RED + "Invalid note ID!")
            return
        note = next((n for n in self.notes if n['id'] == note_id), None)
        if not note:
            print(Fore.RED + "Note not found!")
            return
        print(Fore.YELLOW + f"\nNOTE ID {note_id}")
        print(Fore.CYAN + f"Title: {note['title']}")
        print(f"Content:\n{note['content']}")
        print(f"Tags: {', '.join(note['tags'])}")
        print(f"Created: {note['created']}")
        print(f"Modified: {note['modified']}")
        if note.get('reminder'):
            print(f"Reminder: {note['reminder']}")

    def edit_note(self):
        """Edit an existing note"""
        try:
            note_id = int(input(Fore.CYAN + "Enter note ID to edit: " + Style.RESET_ALL))
        except ValueError:
            print(Fore.RED + "Invalid note ID!")
            return
        note = next((n for n in self.notes if n['id'] == note_id), None)
        if not note:
            print(Fore.RED + "Note not found!")
            return
        
        print(Fore.YELLOW + f"\nEDIT NOTE ID {note_id}")
        new_title = input(Fore.CYAN + f"New Title (leave blank to keep '{note['title']}'): " + Style.RESET_ALL)
        new_content = input(Fore.CYAN + f"New Content (leave blank to keep current content): " + Style.RESET_ALL)
        new_tags_input = input(Fore.CYAN + f"New Tags (comma separated, leave blank to keep current tags): " + Style.RESET_ALL)
        
        if new_title.strip():
            note['title'] = new_title.strip()
        if new_content.strip():
            note['content'] = new_content.strip()
        if new_tags_input.strip():
            note['tags'] = [tag.strip() for tag in new_tags_input.split(",") if tag.strip()]
        
        note['modified'] = datetime.now(pytz.timezone(self.config['timezone'])).isoformat()
        
        self.save_notes()
        print(Fore.GREEN + "Note updated successfully!")

    def delete_note(self):
        """Delete a note"""
        try:
            note_id = int(input(Fore.CYAN + "Enter note ID to delete: " + Style.RESET_ALL))
        except ValueError:
            print(Fore.RED + "Invalid note ID!")
            return
        note = next((n for n in self.notes if n['id'] == note_id), None)
        if not note:
            print(Fore.RED + "Note not found!")
            return
        
        confirm = input(Fore.RED + f"Are you sure you want to delete note '{note['title']}'? (y/n): " + Style.RESET_ALL)
        if confirm.lower() == 'y':
            self.notes = [n for n in self.notes if n['id'] != note_id]
            self.save_notes()
            print(Fore.GREEN + "Note deleted successfully!")
        else:
            print(Fore.YELLOW + "Delete cancelled.")

    def search_notes(self):
        """Search notes by keyword in title, content, or tags"""
        keyword = input(Fore.CYAN + "Enter keyword to search: " + Style.RESET_ALL).lower()
        results = []
        for note in self.notes:
            if (keyword in note['title'].lower() or
                keyword in note['content'].lower() or
                any(keyword in tag.lower() for tag in note['tags'])):
                results.append(note)
        if not results:
            print(Fore.YELLOW + "No matching notes found.")
            return
        print(Fore.YELLOW + f"\nSEARCH RESULTS ({len(results)} found):")
        for note in results:
            print(f"ID: {note['id']} | Title: {note['title']} | Tags: {', '.join(note['tags'])} | Created: {note['created']} | Modified: {note['modified']}")

    def settings_menu(self):
        """Settings menu for encryption, cloud sync, timezone, and Dropbox token"""
        while True:
            print(Fore.YELLOW + "\nSETTINGS")
            print(Fore.CYAN + "1. Toggle Encryption (Currently: " + ("ON" if self.config['encrypted'] else "OFF") + ")")
            print("2. Toggle Cloud Sync (Currently: " + ("ON" if self.config['cloud_sync'] else "OFF") + ")")
            print("3. Set Timezone (Currently: " + self.config['timezone'] + ")")
            print("4. Set Dropbox Token")
            print("5. Back to Main Menu")
            
            choice = input(Fore.CYAN + "Enter your choice (1-5): " + Style.RESET_ALL)
            if choice == '1':
                self.config['encrypted'] = not self.config['encrypted']
                self.setup_encryption()
                self.save_config()
                print(Fore.GREEN + "Encryption toggled. Please restart the app for changes to take effect.")
            elif choice == '2':
                self.config['cloud_sync'] = not self.config['cloud_sync']
                if self.config['cloud_sync']:
                    self.setup_dropbox()
                else:
                    self.dbx = None
                self.save_config()
                print(Fore.GREEN + "Cloud sync toggled.")
            elif choice == '3':
                tz = input(Fore.CYAN + "Enter timezone (e.g. UTC, US/Eastern): " + Style.RESET_ALL)
                try:
                    pytz.timezone(tz)  # Validate timezone
                    self.config['timezone'] = tz
                    self.save_config()
                    print(Fore.GREEN + f"Timezone set to {tz}.")
                except pytz.UnknownTimeZoneError:
                    print(Fore.RED + "Invalid timezone!")
            elif choice == '4':
                token = getpass(Fore.CYAN + "Enter Dropbox token: " + Style.RESET_ALL)
                self.config['dropbox_token'] = token
                self.save_config()
                if self.config['cloud_sync']:
                    self.setup_dropbox()
                print(Fore.GREEN + "Dropbox token updated.")
            elif choice == '5':
                break
            else:
                print(Fore.RED + "Invalid choice. Please enter a number between 1 and 5.")

    def show_menu(self):
        """Display the main menu"""
        print(Fore.YELLOW + "\nNOTE TAKER PRO")
        print(Fore.CYAN + "1. Create Note")
        print("2. List Notes")
        print("3. View Note")
        print("4. Edit Note")
        print("5. Delete Note")
        print("6. Search Notes")
        print("7. Check Reminders")
        print("8. Export Note")
        print("9. Settings")
        print("10. Sync Now")
        print("11. Exit")
    
    def run(self):
        """Run the application"""
        self.check_reminders()  # Check reminders on startup
        
        while True:
            self.show_menu()
            choice = input(Fore.CYAN + "\nEnter your choice (1-11): " + Style.RESET_ALL)
            
            try:
                choice = int(choice)
                if choice == 1:
                    self.create_note()
                elif choice == 2:
                    self.list_notes()
                elif choice == 3:
                    self.view_note()
                elif choice == 4:
                    self.edit_note()
                elif choice == 5:
                    self.delete_note()
                elif choice == 6:
                    self.search_notes()
                elif choice == 7:
                    self.check_reminders()
                elif choice == 8:
                    note_id = input(Fore.CYAN + "Enter note ID to export: " + Style.RESET_ALL)
                    format_type = input(Fore.CYAN + "Format (html/md): " + Style.RESET_ALL)
                    self.export_note(int(note_id), format_type)
                elif choice == 9:
                    self.settings_menu()
                elif choice == 10:
                    self.sync_from_cloud()
                elif choice == 11:
                    print(Fore.YELLOW + "\nGoodbye!")
                    break
                else:
                    print(Fore.RED + "\nInvalid choice. Please enter a number between 1 and 11.")
            except ValueError:
                print(Fore.RED + "\nInvalid input. Please enter a number.")


if __name__ == "__main__":
    app = NoteTakerPro()
    app.run()


