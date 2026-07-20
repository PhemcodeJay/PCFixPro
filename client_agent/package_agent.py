#!/usr/bin/env python3
"""
PCFixPro Agent Package Builder
Creates self-extracting packages for Windows and macOS
"""
import os
import sys
import zipfile
import shutil
from pathlib import Path

class AgentPackager:
    def __init__(self, source_dir, output_dir):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_windows_package(self):
        """Create Windows auto-executing package"""
        print("[Windows] Building package...")
        
        # Create temp package directory
        pkg_dir = self.output_dir / "PCFixPro_Agent_Windows"
        pkg_dir.mkdir(exist_ok=True)
        
        # Files to include
        files = [
            "agent.py",
            "admin_agent.py",
            "requirements.txt",
            "install_service.py",
            "install_silent.bat",
            "install_complete.ps1",
            "setup_agent.bat",
            "CLIENT_README.md"
        ]
        
        for file in files:
            src = self.source_dir / file
            if src.exists():
                try:
                    shutil.copy2(src, pkg_dir / file)
                    print(f"  Added: {file}")
                except Exception as ex:
                    print(f"  Skipped: {file} ({ex})")
        
        # Create auto-run wrapper
        auto_run = pkg_dir / "INSTALL.bat"
        auto_run.write_text("""@echo off
echo Starting PCFixPro Agent Installation...
echo.
REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)
echo.
echo [OK] Running as Administrator
echo.
echo Installing PCFixPro Agent silently...
echo.
call "%~dp0install_silent.bat"
""")
        
        # Create the zip
        zip_path = self.output_dir / "PCFixPro_Agent_Windows.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in pkg_dir.iterdir():
                zf.write(file, file.name)
        
        print(f"[OK] Windows package created: {zip_path}")
        return zip_path
    
    def create_macos_package(self):
        """Create macOS auto-executing package"""
        print("[macOS] Building package...")
        
        # Create temp package directory
        pkg_dir = self.output_dir / "PCFixPro_Agent_macOS"
        pkg_dir.mkdir(exist_ok=True)
        
        # Files to include
        files = [
            "macos_agent.py",
            "requirements.txt",
            "install_macos.sh",
            "com.pcfixpro.agent.plist",
            "CLIENT_README.md"
        ]
        
        for file in files:
            src = self.source_dir / file
            if src.exists():
                try:
                    shutil.copy2(src, pkg_dir / file)
                    print(f"  Added: {file}")
                except Exception as ex:
                    print(f"  Skipped: {file} ({ex})")
        
        # Make install script executable
        install_script = pkg_dir / "install_macos.sh"
        if install_script.exists():
            install_script.chmod(0o755)
        
        # Create auto-run wrapper
        auto_run = pkg_dir / "INSTALL.command"
        auto_run.write_text("""#!/bin/bash
# PCFixPro Agent Auto-Installer for macOS

cd "$(dirname "$0")"

echo "========================================"
echo "PCFixPro Agent Installation"
echo "========================================"
echo ""
echo "This will install the PCFixPro Remote Support Agent"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "[INFO] Requesting administrator privileges..."
    sudo "$0"
    exit $?
fi

echo "[OK] Running as Administrator"
echo ""
echo "Starting installation..."
echo ""

./install_macos.sh

echo ""
echo "Press any key to exit..."
read -n 1
""")
        auto_run.chmod(0o755)
        
        # Create the zip
        zip_path = self.output_dir / "PCFixPro_Agent_macOS.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in pkg_dir.iterdir():
                zf.write(file, file.name)
        
        print(f"[OK] macOS package created: {zip_path}")
        return zip_path
    
    def create_universal_package(self):
        """Create universal package with both Windows and macOS installers"""
        print("[Universal] Building cross-platform package...")
        
        # Create temp directory
        pkg_dir = self.output_dir / "PCFixPro_Agent_Universal"
        pkg_dir.mkdir(exist_ok=True)
        
        # Copy all client_agent files
        for item in self.source_dir.iterdir():
            if item.is_file() and item.suffix in ['.py', '.sh', '.bat', '.ps1', '.txt', '.md', '.plist']:
                try:
                    shutil.copy2(item, pkg_dir / item.name)
                    print(f"  Added: {item.name}")
                except Exception as ex:
                    print(f"  Skipped: {item.name} ({ex})")
        
        # Create Windows auto-run wrapper
        install_bat = pkg_dir / "INSTALL.bat"
        install_bat.write_text("""@echo off
echo Starting PCFixPro Agent Installation...
echo.
REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)
echo.
echo [OK] Running as Administrator
echo.
echo Installing PCFixPro Agent silently...
echo.
call "%~dp0install_silent.bat"
""")
        
        # Create macOS auto-run wrapper
        install_cmd = pkg_dir / "INSTALL.command"
        install_cmd.write_text("""#!/bin/bash
# PCFixPro Agent Auto-Installer for macOS

cd "$(dirname "$0")"

echo "========================================"
echo "PCFixPro Agent Installation"
echo "========================================"
echo ""
echo "This will install the PCFixPro Remote Support Agent"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "[INFO] Requesting administrator privileges..."
    sudo "$0"
    exit $?
fi

echo "[OK] Running as Administrator"
echo ""
echo "Starting installation..."
echo ""

./install_macos.sh

echo ""
echo "Press any key to exit..."
read -n 1
""")
        
        # Make script executable
        install_cmd.chmod(0o755)
        
        # Update README to match our files
        readme = pkg_dir / "README.txt"
        readme.write_text("""PCFixPro Remote Support Agent
===============================

WINDOWS USERS:
1. Double-click: INSTALL.bat
2. Follow the prompts
3. Installation runs automatically

macOS USERS:
1. Double-click: INSTALL.command
2. Enter your password when prompted
3. Installation runs automatically

After installation:
- The agent will appear in your Command & Control Center
- Logs are available on your desktop
- No further action required

Need help? Contact PCFixPro ICT Services
""")
        
        # Create the zip
        zip_path = self.output_dir / "PCFixPro_Agent_Universal.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in pkg_dir.iterdir():
                zf.write(file, file.name)
        
        print(f"[OK] Universal package created: {zip_path}")
        return zip_path
    
    def build_all(self):
        """Build all packages"""
        print("=" * 50)
        print("PCFixPro Agent Package Builder")
        print("=" * 50)
        print()
        
        self.create_windows_package()
        print()
        self.create_macos_package()
        print()
        self.create_universal_package()
        
        print()
        print("=" * 50)
        print("All packages built successfully!")
        print(f"Output directory: {self.output_dir}")
        print("=" * 50)

if __name__ == "__main__":
    # Get script directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / "dist"
    
    packager = AgentPackager(script_dir, output_dir)
    packager.build_all()