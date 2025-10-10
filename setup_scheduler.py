"""
Setup script for configuring the daily updater scheduler
Provides options for different scheduling methods
"""

import os
import sys
import platform
from pathlib import Path

def create_cron_job():
    """Create a cron job for Unix-like systems"""
    script_path = Path(__file__).parent / "daily_updater.py"
    python_path = sys.executable
    
    cron_line = f"0 9 * * * cd {script_path.parent} && {python_path} daily_updater.py >> daily_updater.log 2>&1"
    
    print("Add this line to your crontab (run 'crontab -e'):")
    print(cron_line)
    print("\nThis will run the updater daily at 9:00 AM")

def create_windows_task():
    """Instructions for Windows Task Scheduler"""
    script_path = Path(__file__).parent / "daily_updater.py"
    python_path = sys.executable
    
    print("To create a Windows scheduled task:")
    print("1. Open Task Scheduler")
    print("2. Create Basic Task")
    print("3. Set trigger to Daily at 9:00 AM")
    print(f"4. Set action to start program: {python_path}")
    print(f"5. Set arguments: {script_path}")
    print(f"6. Set start in directory: {script_path.parent}")

def create_systemd_service():
    """Create systemd service and timer for Linux"""
    service_content = f"""[Unit]
Description=Pokemon Portfolio Daily Updater
After=network.target

[Service]
Type=oneshot
User={os.getenv('USER', 'pokemon')}
WorkingDirectory={Path(__file__).parent}
ExecStart={sys.executable} daily_updater.py
StandardOutput=append:/var/log/pokemon-updater.log
StandardError=append:/var/log/pokemon-updater.log

[Install]
WantedBy=multi-user.target
"""

    timer_content = """[Unit]
Description=Run Pokemon Portfolio Updater daily
Requires=pokemon-updater.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
"""

    print("Systemd service file content (save as /etc/systemd/system/pokemon-updater.service):")
    print(service_content)
    print("\nSystemd timer file content (save as /etc/systemd/system/pokemon-updater.timer):")
    print(timer_content)
    print("\nThen run:")
    print("sudo systemctl daemon-reload")
    print("sudo systemctl enable pokemon-updater.timer")
    print("sudo systemctl start pokemon-updater.timer")

def main():
    print("Pokemon Portfolio Daily Updater Setup")
    print("=====================================")
    print()
    
    system = platform.system().lower()
    
    print("Choose scheduling method:")
    print("1. Manual run (run once)")
    print("2. Built-in scheduler (keeps running)")
    if system in ['linux', 'darwin']:
        print("3. Cron job (Unix/Linux/macOS)")
        print("4. Systemd service (Linux only)")
    elif system == 'windows':
        print("3. Windows Task Scheduler")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("To run manually: python daily_updater.py")
    elif choice == "2":
        print("To run with built-in scheduler: python daily_updater.py --scheduler")
        print("This will keep the process running and update daily at 9:00 AM")
    elif choice == "3":
        if system == 'windows':
            create_windows_task()
        else:
            create_cron_job()
    elif choice == "4" and system == 'linux':
        create_systemd_service()
    else:
        print("Invalid choice or not available on your system")

if __name__ == "__main__":
    main()
