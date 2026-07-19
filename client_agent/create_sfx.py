#!/usr/bin/env python3
"""
PCFixPro SFX (Self-Extracting) Creator
Creates self-extracting executables that auto-install the agent
"""
import os
import sys
import zipfile
from pathlib import Path

def create_windows_sfx():
    """Create a Windows self-extracting EXE"""
    script_dir = Path(__file__).parent
    dist_dir = script_dir / "dist"
    zip_path = dist_dir / "PCFixPro_Agent_Universal.zip"
    sfx_path = dist_dir / "PCFixPro_Installer.exe"
    
    if not zip_path.exists():
        print("[ERROR] ZIP file not found. Run package_agent.py first.")
        return False
    
    # Create SFX using 7-Zip (if available) or simple batch wrapper
    sfx_script = script_dir / "sfx_installer.nsi"
    
    # Create NSIS script for SFX
    nsis_content = f"""!include LogicLib
!include FileFunc.nsh
!include WinVer.nsh

!define APP_NAME "PCFixPro Remote Support Agent"
!define ZIP_FILE "{zip_path.name}"

OutFile "{sfx_path}"
InstallDir $TEMP\\PCFixPro_Installer
RequestExecutionLevel admin
SilentInstall silent

Page instfiles

Section
    SetOutPath "$INSTDIR"
    
    ; Extract ZIP
    InitPluginsDir
    NSISdl::download "" "$INSTDIR\\{zip_path.name}"
    
    ; If we have the ZIP locally, copy it
    CopyFiles /SILENT "$%TEMP%\\\\{zip_path.name}" "$INSTDIR"
    
    ; Extract and run installer
    SetShellVarContext all
    
    ; Run the silent installer
    ExecWait '"$INSTDIR\\\\install_silent.bat"'
    
    ; Cleanup
    RMDir /r "$INSTDIR"
SectionEnd
"""
    
    # Write the SFX script
    sfx_script.write_text(nsis_content)
    print(f"[INFO] NSIS SFX script created: {sfx_script}")
    print("[NOTE] Install NSIS from nsis.sourceforge.net to build the EXE")
    
    return True

def create_simple_batch_sfx():
    """Create a simple batch-based SFX (works without external tools)"""
    script_dir = Path(__file__).parent
    dist_dir = script_dir / "dist"
    downloads_dir = script_dir.parent / "downloads"
    
    zip_path = dist_dir / "PCFixPro_Agent_Universal.zip"
    sfx_bat = downloads_dir / "PCFixPro_AutoInstall.bat"
    
    if not zip_path.exists():
        print("[ERROR] ZIP file not found. Run package_agent.py first.")
        return False
    
    # Create a batch file that auto-extracts and installs
    # Uses relative path so it works when in the same folder as the ZIP
    batch_content = """@echo off
:: PCFixPro Auto-Installer
:: Extracts ZIP and runs installer automatically
:: This file should be in the same folder as PCFixPro_Agent_Universal.zip

setlocal enabledelayedexpansion

echo ========================================
echo PCFixPro Remote Support Agent Auto-Installer
echo ========================================
echo.

:: Check admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)

echo [OK] Running with administrator privileges
echo.

:: Extract ZIP to temp folder (uses same folder as this .bat file)
set "TEMP_DIR=%TEMP%\\PCFixPro_AutoInstall"
echo [1/3] Extracting installer...
powershell -Command "Expand-Archive -Path '%~dp0PCFixPro_Agent_Universal.zip' -DestinationPath '%TEMP_DIR%' -Force"

:: Run installer
echo [2/3] Running silent installer...
cd /d "%TEMP_DIR%"
call install_silent.bat

:: Cleanup
echo [3/3] Cleaning up...
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo ========================================
echo Installation Complete! Agent auto-connects to dashboard.
echo ========================================
pause
"""
    
    downloads_dir.mkdir(exist_ok=True)
    sfx_bat.write_text(batch_content)
    print(f"[OK] Created: {sfx_bat}")
    print("[INFO] Send this .bat file to clients - it auto-extracts and installs!")
    
    return True

if __name__ == "__main__":
    print("PCFixPro SFX Creator")
    print("=" * 40)
    print()
    
    # Create simple batch SFX (works everywhere)
    create_simple_batch_sfx()
    
    print()
    print("[NOTE] For true EXE SFX, install NSIS and compile sfx_installer.nsi")