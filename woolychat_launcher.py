#!/usr/bin/env python3
"""
WoolyChat Launcher with Setup Wizard
A graphical launcher that handles first-time setup and server management
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import webbrowser
import re
import os
import sys
import time
import platform
from pathlib import Path

# Import your existing modules
try:
    # Import standard library modules first
    import calendar
    import datetime
    import json
    import os
    import sys
    import time
    import threading
    import subprocess
    import webbrowser
    import re
    import socket
    
    # Import Flask and SQLAlchemy first to ensure they're available
    import flask
    import flask_sqlalchemy
    import requests
    
    # Import your custom modules
    from models import init_db, User, db
    from utils import get_available_port
    import ollama_chat
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install flask flask-sqlalchemy requests PyPDF2 python-docx")
    
    # Also check if it's a standard library module issue
    if "calendar" in str(e) or "datetime" in str(e):
        print("\nThis seems to be a Python standard library issue.")
        print("If running from a PyInstaller bundle, this may be a packaging problem.")
        print("Try rebuilding with the updated .spec file.")
    
    sys.exit(1)

class WoolyChatLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WoolyChat v0.4 Launcher")
        self.root.geometry("600x600")
        self.root.resizable(False, False)
        
        # State management
        self.flask_process = None
        self.flask_port = None
        self.setup_complete = False
        self.ollama_running = False
        
        # Setup data directory for database and uploads
        self.setup_data_directory()
        
        # Initialize database and check setup status
        self.init_database()
        self.check_setup_status()
        
        # Create UI
        self.create_ui()
        
        # Start with appropriate screen
        if self.setup_complete:
            self.show_main_screen()
        else:
            self.show_setup_wizard()
    
    def setup_data_directory(self):
        """Setup a writable data directory for the app"""
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller bundle
            if sys.platform == 'darwin':  # macOS
                # Use ~/Library/Application Support/WoolyChat
                home = os.path.expanduser('~')
                self.data_dir = os.path.join(home, 'Library', 'Application Support', 'WoolyChat')
            elif sys.platform == 'win32':  # Windows
                # Use %APPDATA%/WoolyChat
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.data_dir = os.path.join(appdata, 'WoolyChat')
            else:  # Linux
                # Use ~/.config/WoolyChat
                home = os.path.expanduser('~')
                self.data_dir = os.path.join(home, '.config', 'WoolyChat')
        else:
            # Running from source - use current directory
            self.data_dir = os.getcwd()
        
        # Create the data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create uploads subdirectory
        self.uploads_dir = os.path.join(self.data_dir, 'uploads')
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        # Set database path
        self.db_path = os.path.join(self.data_dir, 'ollama_chat.db')
        
        print(f"📁 Data directory: {self.data_dir}")
        print(f"📁 Database path: {self.db_path}")
        print(f"📁 Uploads directory: {self.uploads_dir}")
    
    def init_database(self):
        """Initialize database with Flask app context"""
        try:
            # Create a minimal Flask app for database initialization
            from flask import Flask
            app = Flask(__name__)
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            app.config['UPLOAD_FOLDER'] = self.uploads_dir
            
            with app.app_context():
                # First, check if the database exists and handle migration
                db_exists = os.path.exists(self.db_path)
                
                if db_exists:
                    # Database exists, check if we need to add the setup_complete column
                    import sqlite3
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    try:
                        # Check if setup_complete column exists
                        cursor.execute("PRAGMA table_info(user)")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        if 'setup_complete' not in columns:
                            # Add the missing column
                            cursor.execute("ALTER TABLE user ADD COLUMN setup_complete BOOLEAN DEFAULT 0")
                            conn.commit()
                            print("Added setup_complete column to existing database")
                        
                    except sqlite3.Error as e:
                        print(f"SQLite migration error: {e}")
                    finally:
                        conn.close()
                
                # Now initialize with SQLAlchemy
                init_db(app)
                    
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
            sys.exit(1)
    
    def check_setup_status(self):
        """Check if setup has been completed"""
        try:
            from flask import Flask
            app = Flask(__name__)
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            
            with app.app_context():
                from models import db, User
                db.init_app(app)
                
                # Now it's safe to query since migration happened in init_database()
                user = User.query.first()
                if user:
                    self.setup_complete = user.setup_complete
                    print(f"Setup status check: user exists, setup_complete = {self.setup_complete}")
                else:
                    self.setup_complete = False
                    print("Setup status check: no users found, setup_complete = False")
                    
        except Exception as e:
            print(f"Error checking setup status: {e}")
            self.setup_complete = False
    
    def mark_setup_complete(self):
        """Mark setup as complete in database"""
        try:
            from flask import Flask
            app = Flask(__name__)
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            
            with app.app_context():
                from models import db, User
                db.init_app(app)
                
                # Get existing user or create new one
                user = User.query.first()
                if user:
                    user.setup_complete = True
                    print("Marked existing user setup as complete")
                else:
                    # Create a default admin user with setup complete
                    user = User(username='admin', setup_complete=True)
                    db.session.add(user)
                    print("Created new admin user with setup complete")
                
                db.session.commit()
                
        except Exception as e:
            print(f"Error marking setup complete: {e}")
    
    def create_ui(self):
        """Create the main UI structure"""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            self.main_frame, 
            text="🐑 WoolyChat", 
            font=("Helvetica", 24, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Content frame (will be populated based on state)
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        self.content_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Status frame
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
    
    def clear_content_frame(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_setup_wizard(self):
        """Show the initial setup wizard"""
        self.clear_content_frame()
        
        # Setup wizard content
        setup_label = ttk.Label(
            self.content_frame, 
            text="Welcome to WoolyChat!\nLet's set up your AI chat environment.",
            font=("Helvetica", 12),
            justify=tk.CENTER
        )
        setup_label.grid(row=0, column=0, pady=(0, 20))
        
        # Progress frame
        self.progress_frame = ttk.Frame(self.content_frame)
        self.progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        self.progress_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(
            self.content_frame, 
            height=15, 
            width=70,
            state=tk.DISABLED
        )
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Button frame
        button_frame = ttk.Frame(self.content_frame)
        button_frame.grid(row=3, column=0)
        
        self.start_setup_btn = ttk.Button(
            button_frame, 
            text="Start Setup", 
            command=self.start_setup_process
        )
        self.start_setup_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.skip_setup_btn = ttk.Button(
            button_frame, 
            text="Skip Setup", 
            command=self.skip_setup
        )
        self.skip_setup_btn.grid(row=0, column=1)
    
    def log_message(self, message):
        """Add message to log output"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def start_setup_process(self):
        """Start the setup process in a separate thread"""
        self.start_setup_btn.config(state=tk.DISABLED)
        self.progress.start()
        
        setup_thread = threading.Thread(target=self.run_setup_checks, daemon=True)
        setup_thread.start()
    
    def run_setup_checks(self):
        """Run all setup checks"""
        try:
            self.log_message("🔍 Starting WoolyChat setup...")
            
            # Step 1: Check if Ollama is installed
            self.log_message("\n📦 Checking if Ollama is installed...")
            ollama_installed = self.check_ollama_installed()
            
            if not ollama_installed:
                self.log_message("❌ Ollama not found")
                if self.ask_user_install_ollama():
                    return  # User chose to install Ollama manually
            else:
                self.log_message("✅ Ollama is installed")
            
            # Step 2: Check if Ollama is running
            self.log_message("\n🔄 Checking if Ollama service is running...")
            if not self.ensure_ollama_running():
                self.log_message("❌ Could not start Ollama service")
                return
            
            # Step 3: Check installed models
            self.log_message("\n🤖 Checking installed models...")
            models = self.get_installed_models()
            
            if not models:
                self.log_message("❌ No models found")
                self.handle_no_models()
            else:
                self.log_message(f"✅ Found {len(models)} models:")
                for model in models[:5]:  # Show first 5
                    self.log_message(f"   • {model}")
                if len(models) > 5:
                    self.log_message(f"   ... and {len(models) - 5} more")
                
                self.setup_complete_success()
            
        except Exception as e:
            self.log_message(f"❌ Setup error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Setup Error", str(e)))
        finally:
            self.root.after(0, lambda: self.progress.stop())
    
    def find_ollama_path(self):
        """Find the Ollama executable in common installation locations"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            common_paths = [
                '/usr/local/bin/ollama',  # Homebrew default
                '/opt/homebrew/bin/ollama',  # Apple Silicon Homebrew
                '/usr/bin/ollama',  # System installation
                os.path.expanduser('~/.local/bin/ollama'),  # User installation
                '/Applications/Ollama.app/Contents/Resources/ollama',  # Official installer
            ]
            
            # First try the system PATH using 'which'
            try:
                result = subprocess.run(['which', 'ollama'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ollama_path = result.stdout.strip()
                    if os.path.exists(ollama_path):
                        return ollama_path
            except:
                pass
            
            # Then check common macOS locations
            for path in common_paths:
                if os.path.exists(path):
                    return path
                    
        elif system == "Windows":
            # For Windows, use the specific installation path
            windows_ollama_path = r"C:\Users\haasrr\AppData\Local\Programs\Ollama\ollama.exe"
            if os.path.exists(windows_ollama_path):
                return windows_ollama_path
            
            # Alternatively, try to use 'where' command (Windows equivalent of 'which')
            try:
                result = subprocess.run(['where', 'ollama'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ollama_path = result.stdout.strip().split('\n')[0]  # Get first result
                    if os.path.exists(ollama_path):
                        return ollama_path
            except:
                pass
        
        return None
    
    def run_ollama_command(self, args, **kwargs):
        """Run an ollama command with the correct path"""
        ollama_path = self.find_ollama_path()
        if not ollama_path:
            raise FileNotFoundError("Ollama not found in any common locations")
        
        cmd = [ollama_path] + args
        return subprocess.run(cmd, **kwargs)
    
    def check_ollama_installed(self):
        """Check if Ollama is installed"""
        try:
            result = self.run_ollama_command(
                ['--version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return "ollama version is" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def ask_user_install_ollama(self):
        """Ask user if they want to install Ollama"""
        def on_install():
            self.log_message("🌐 Opening Ollama download page...")
            webbrowser.open("https://ollama.com")
            self.log_message("📝 Please install Ollama and restart WoolyChat")
            install_dialog.destroy()
        
        def on_skip():
            self.log_message("⏭️ Skipping Ollama installation")
            install_dialog.destroy()
        
        install_dialog = tk.Toplevel(self.root)
        install_dialog.title("Install Ollama")
        install_dialog.geometry("400x200")
        install_dialog.transient(self.root)
        install_dialog.grab_set()
        
        ttk.Label(
            install_dialog, 
            text="Ollama is required for WoolyChat to work.\nWould you like to download it now?",
            justify=tk.CENTER
        ).pack(pady=20)
        
        button_frame = ttk.Frame(install_dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Download Ollama", command=on_install).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Skip", command=on_skip).pack(side=tk.LEFT, padx=10)
        
        return True
    
    def ensure_ollama_running(self):
        """Ensure Ollama service is running"""
        try:
            # First check if already running
            result = self.run_ollama_command(
                ['list'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                self.ollama_running = True
                return True
        except:
            pass
        
        # Try to start Ollama
        self.log_message("🚀 Starting Ollama service...")
        try:
            ollama_path = self.find_ollama_path()
            if not ollama_path:
                self.log_message("❌ Cannot find Ollama executable")
                return False
                
            subprocess.Popen([ollama_path, 'serve'], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            time.sleep(3)  # Give it time to start
            
            # Check again
            result = self.run_ollama_command(
                ['list'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                self.ollama_running = True
                self.log_message("✅ Ollama service started")
                return True
        except Exception as e:
            self.log_message(f"❌ Failed to start Ollama: {str(e)}")
        
        return False
    
    def get_installed_models(self):
        """Get list of installed Ollama models"""
        try:
            result = self.run_ollama_command(
                ['list'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return []
            
            # Check if header line matches expected format
            header = lines[0]
            if not re.match(r"NAME\s*ID\s*SIZE\s*MODIFIED", header):
                return []
            
            # Extract model names from subsequent lines
            models = []
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
            
            return models
            
        except Exception as e:
            self.log_message(f"Error checking models: {str(e)}")
            return []
    
    def handle_no_models(self):
        """Handle case where no models are installed"""
        def show_model_selection():
            model_dialog = tk.Toplevel(self.root)
            model_dialog.title("Install AI Model")
            model_dialog.geometry("500x400")
            model_dialog.transient(self.root)
            model_dialog.grab_set()
            
            ttk.Label(
                model_dialog, 
                text="No AI models found. Please choose a model to install:",
                font=("Helvetica", 12, "bold")
            ).pack(pady=10)
            
            # Model options
            model_var = tk.StringVar(value="gemma3:4b")

            models = [
                ("gemma3:4b", "Overall/best all-around (3.3 GB)", "Recommended for most users"),
                ("llama3.2:3b", "Lightweight general tasks (2.0 GB)", "Cannot analyze images"),
                ("granite3.3:8b", "Strong instruction-following (4.9 GB)", "Cannot analyze images")
            ]
            
            for model_name, description, note in models:
                frame = ttk.Frame(model_dialog)
                frame.pack(fill=tk.X, padx=20, pady=5)
                
                ttk.Radiobutton(
                    frame, 
                    text=f"{model_name} - {description}",
                    variable=model_var, 
                    value=model_name
                ).pack(anchor=tk.W)
                
                ttk.Label(
                    frame, 
                    text=note, 
                    font=("Helvetica", 9),
                    foreground="gray"
                ).pack(anchor=tk.W, padx=20)
            
            def install_selected_model():
                selected_model = model_var.get()
                model_dialog.destroy()
                self.install_model(selected_model)
            
            def skip_model_install():
                model_dialog.destroy()
                self.log_message("⏭️ Skipping model installation")
                self.setup_complete_success()
            
            button_frame = ttk.Frame(model_dialog)
            button_frame.pack(pady=20)
            
            ttk.Button(
                button_frame, 
                text="Install Model", 
                command=install_selected_model
            ).pack(side=tk.LEFT, padx=10)
            
            ttk.Button(
                button_frame, 
                text="Skip", 
                command=skip_model_install
            ).pack(side=tk.LEFT, padx=10)
        
        self.root.after(0, show_model_selection)
    
    def install_model(self, model_name):
        """Install the specified model"""
        self.log_message(f"\n⬇️ Installing model: {model_name}")
        self.log_message("This may take several minutes depending on your internet connection...")
        
        def run_install():
            try:
                ollama_path = self.find_ollama_path()
                if not ollama_path:
                    self.root.after(0, lambda: self.log_message("❌ Cannot find Ollama executable"))
                    return
                
                process = subprocess.Popen(
                    [ollama_path, 'pull', model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True
                )
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.root.after(0, lambda o=output.strip(): self.log_message(f"   {o}"))
                
                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_message(f"✅ Successfully installed {model_name}"))
                    self.root.after(0, self.setup_complete_success)
                else:
                    self.root.after(0, lambda: self.log_message(f"❌ Failed to install {model_name}"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"❌ Installation error: {str(e)}"))
        
        install_thread = threading.Thread(target=run_install, daemon=True)
        install_thread.start()
    
    def setup_complete_success(self):
        """Handle successful setup completion"""
        self.mark_setup_complete()
        self.setup_complete = True
        self.log_message("\n🎉 Setup completed successfully!")
        self.log_message("You can now start chatting with AI models.")
        
        # Update UI
        self.start_setup_btn.config(state=tk.NORMAL, text="Setup Complete")
        
        # Show continue button
        continue_btn = ttk.Button(
            self.content_frame, 
            text="Continue to WoolyChat", 
            command=self.show_main_screen
        )
        continue_btn.grid(row=4, column=0, pady=10)
    
    def skip_setup(self):
        """Skip the setup process"""
        if messagebox.askyesno("Skip Setup", "Are you sure you want to skip setup?\nWoolyChat may not work properly without proper configuration."):
            self.mark_setup_complete()
            self.setup_complete = True
            self.show_main_screen()
    
    def show_main_screen(self):
        """Show the main launcher screen"""
        self.clear_content_frame()
        
        # Data location info
        info_frame = ttk.LabelFrame(self.content_frame, text="Data Location", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        
        ttk.Label(info_frame, text="Database & Files:").grid(row=0, column=0, sticky=tk.W)
        data_label = ttk.Label(info_frame, text=self.data_dir, foreground="#039dfc")
        data_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Make the path clickable to open in Finder/Explorer
        def open_data_folder():
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', self.data_dir])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['explorer', self.data_dir])
            else:  # Linux
                subprocess.run(['xdg-open', self.data_dir])
        
        data_label.bind("<Button-1>", lambda e: open_data_folder())
        data_label.bind("<Enter>", lambda e: data_label.config(cursor="hand2"))
        data_label.bind("<Leave>", lambda e: data_label.config(cursor=""))
        
        # Server status
        status_frame = ttk.LabelFrame(self.content_frame, text="Server Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Flask Server:").grid(row=0, column=0, sticky=tk.W)
        self.flask_status_label = ttk.Label(status_frame, text="Stopped", foreground="red")
        self.flask_status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Ollama Service:").grid(row=1, column=0, sticky=tk.W)
        self.ollama_status_label = ttk.Label(status_frame, text="Checking...", foreground="orange")
        self.ollama_status_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Control buttons
        control_frame = ttk.LabelFrame(self.content_frame, text="Controls", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.start_server_btn = ttk.Button(
            control_frame, 
            text="Start WoolyChat Server", 
            command=self.start_server
        )
        self.start_server_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_server_btn = ttk.Button(
            control_frame, 
            text="Stop Server", 
            command=self.stop_server,
            state=tk.DISABLED
        )
        self.stop_server_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.open_browser_btn = ttk.Button(
            control_frame, 
            text="Open in Browser", 
            command=self.open_browser,
            state=tk.DISABLED
        )
        self.open_browser_btn.grid(row=0, column=2)
        
        # Log output
        log_frame = ttk.LabelFrame(self.content_frame, text="Server Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.server_log = scrolledtext.ScrolledText(
            log_frame, 
            height=12, 
            width=70,
            state=tk.DISABLED
        )
        self.server_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Check initial status
        self.check_ollama_status()
    
    def check_ollama_status(self):
        """Check if Ollama is running"""
        try:
            result = self.run_ollama_command(
                ['list'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                self.ollama_status_label.config(text="Running", foreground="green")
                self.ollama_running = True
            else:
                self.ollama_status_label.config(text="Stopped", foreground="red")
                self.ollama_running = False
        except:
            self.ollama_status_label.config(text="Not Available", foreground="red")
            self.ollama_running = False
    
    def start_server(self):
        """Start the Flask server"""
        try:
            # First ensure Ollama is running
            if not self.ollama_running:
                self.server_log_message("Starting Ollama service...")
                ollama_path = self.find_ollama_path()
                if ollama_path:
                    subprocess.Popen([ollama_path, 'serve'])
                    time.sleep(2)
                    self.check_ollama_status()
                else:
                    self.server_log_message("❌ Cannot find Ollama executable")
            
            # Find available port
            self.flask_port = get_available_port(5000)
            self.server_log_message(f"Starting WoolyChat server on port {self.flask_port}...")
            
            # Find the Flask script
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller bundle - Flask app should be bundled
                script_dir = sys._MEIPASS
                self.server_log_message(f"Running from bundle: {script_dir}")
                
                # Try to import and run Flask directly instead of subprocess
                self.start_flask_directly()
                return
            else:
                # Running from source
                script_dir = os.path.dirname(os.path.abspath(__file__))
                server_script = os.path.join(script_dir, 'ollama_chat.py')
                
                if not os.path.exists(server_script):
                    raise FileNotFoundError(f"Flask script not found: {server_script}")
                
                self.server_log_message(f"Using Flask script: {server_script}")
            
            # Set environment variables for Flask
            env = os.environ.copy()
            env['FLASK_PORT'] = str(self.flask_port)
            env['WOOLYCHAT_DATA_DIR'] = self.data_dir
            env['WOOLYCHAT_DB_PATH'] = self.db_path
            env['WOOLYCHAT_UPLOADS_DIR'] = self.uploads_dir
            
            self.flask_process = subprocess.Popen(
                [sys.executable, server_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=script_dir
            )
            
            # Wait a moment for server to start
            time.sleep(2)
            
            # Check if the process is still running
            if self.flask_process.poll() is not None:
                self.server_log_message("❌ Flask process terminated immediately")
                return
            
            # Test if server is actually responding
            self.test_server_connection()
            
            # Update UI
            self.flask_status_label.config(text=f"Running (port {self.flask_port})", foreground="green")
            self.start_server_btn.config(state=tk.DISABLED)
            self.stop_server_btn.config(state=tk.NORMAL)
            self.open_browser_btn.config(state=tk.NORMAL)
            
            # Start monitoring server output
            self.monitor_server_output()
            
        except Exception as e:
            self.server_log_message(f"Error starting server: {str(e)}")
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
    
    def start_flask_directly(self):
        """Start Flask directly in a thread when running from bundle"""
        def run_flask():
            try:
                self.server_log_message("Starting Flask directly in thread...")
                
                # Set environment variables
                os.environ['WOOLYCHAT_DATA_DIR'] = self.data_dir
                os.environ['WOOLYCHAT_DB_PATH'] = self.db_path
                os.environ['WOOLYCHAT_UPLOADS_DIR'] = self.uploads_dir
                
                # Import and create the Flask app
                from ollama_chat import create_app
                app = create_app()
                
                self.server_log_message(f"Flask app created, starting on port {self.flask_port}")
                
                # Run the Flask app
                app.run(host='127.0.0.1', port=self.flask_port, debug=False, use_reloader=False)
                
            except Exception as e:
                self.root.after(0, lambda: self.server_log_message(f"❌ Flask error: {str(e)}"))
                import traceback
                self.root.after(0, lambda: self.server_log_message(traceback.format_exc()))
        
        # Start Flask in a daemon thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Wait a moment then test connection
        def delayed_test():
            time.sleep(3)
            self.root.after(0, self.test_server_connection)
            self.root.after(0, lambda: self.flask_status_label.config(text=f"Running (port {self.flask_port})", foreground="green"))
            self.root.after(0, lambda: self.start_server_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.stop_server_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.open_browser_btn.config(state=tk.NORMAL))
        
        test_thread = threading.Thread(target=delayed_test, daemon=True)
        test_thread.start()
    
    def test_server_connection(self):
        """Test if the Flask server is actually responding"""
        try:
            import urllib.request
            url = f"http://127.0.0.1:{self.flask_port}/health"
            
            self.server_log_message(f"Testing connection to {url}...")
            
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    self.server_log_message("✅ Server is responding!")
                    return True
                else:
                    self.server_log_message(f"⚠️ Server returned status {response.status}")
                    return False
                    
        except Exception as e:
            self.server_log_message(f"❌ Server test failed: {str(e)}")
            return False
    
    def stop_server(self):
        """Stop the Flask server"""
        if self.flask_process:
            try:
                self.flask_process.terminate()
                self.flask_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.flask_process.kill()
            
            self.flask_process = None
            self.flask_port = None
        
        # Update UI
        self.flask_status_label.config(text="Stopped", foreground="red")
        self.start_server_btn.config(state=tk.NORMAL)
        self.stop_server_btn.config(state=tk.DISABLED)
        self.open_browser_btn.config(state=tk.DISABLED)
        
        self.server_log_message("Server stopped")
    
    def open_browser(self):
        """Open WoolyChat in the browser"""
        if self.flask_port:
            url = f"http://127.0.0.1:{self.flask_port}"
            
            # Test connection first
            if self.test_server_connection():
                webbrowser.open(url)
                self.server_log_message(f"Opened {url} in browser")
            else:
                self.server_log_message(f"❌ Cannot connect to server at {url}")
                messagebox.showerror("Connection Error", 
                    f"Cannot connect to WoolyChat server at {url}\n\n"
                    "Please check the server log for errors.")
        else:
            messagebox.showerror("Server Error", "No server port available")
    
    def server_log_message(self, message):
        """Add message to server log"""
        self.server_log.config(state=tk.NORMAL)
        self.server_log.insert(tk.END, f"{message}\n")
        self.server_log.see(tk.END)
        self.server_log.config(state=tk.DISABLED)
        self.root.update()
    
    def monitor_server_output(self):
        """Monitor Flask server output in a separate thread"""
        def read_output():
            if self.flask_process and self.flask_process.stdout:
                try:
                    while self.flask_process.poll() is None:
                        line = self.flask_process.stdout.readline()
                        if line:
                            self.root.after(0, lambda l=line.strip(): self.server_log_message(l))
                except:
                    pass
        
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
    
    def on_closing(self):
        """Handle window closing"""
        if self.flask_process:
            self.stop_server()
        self.root.destroy()
    
    def run(self):
        """Run the launcher"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    launcher = WoolyChatLauncher()
    launcher.run()