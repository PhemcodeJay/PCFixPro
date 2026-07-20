@echo off
:: Copy screenconnect.zip to downloads folder
echo Copying screenconnect.zip to downloads...
copy "C:\Users\Bossman\Desktop\screenconnect.zip" "c:\Users\Bossman\Documents\PCFixPro\downloads\screenconnect.zip"
if %errorlevel% equ 0 (
    echo SUCCESS: screenconnect.zip copied to downloads folder
) else (
    echo FAILED: Could not copy file
    echo The file is available at: C:\Users\Bossman\Desktop\screenconnect.zip
)