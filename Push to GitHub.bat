@echo off
title Push Certificate Generator to GitHub for Render
cd /d "%~dp0"

echo ========================================================
echo  PUSH VISUAL CERTIFICATE GENERATOR TO GITHUB FOR RENDER
echo ========================================================
echo.
echo 1. Go to https://github.com/new in your browser.
echo 2. Name your repository (e.g. certificate-generator).
echo 3. Leave it Public (or Private) and DO NOT check "Add a README".
echo 4. Copy the repository HTTPS URL (e.g. https://github.com/username/certificate-generator.git).
echo.
set /p REPO_URL="Paste your GitHub Repository URL here: "

if "%REPO_URL%"=="" (
    echo No URL entered. Aborting.
    pause
    exit /b
)

echo.
echo Configuring remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main

echo.
echo Pushing code to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ----------------------------------------------------
    echo Push failed. Please check your GitHub permissions or sign in.
    echo ----------------------------------------------------
) else (
    echo.
    echo ====================================================
    echo SUCCESS! Your code is now live on GitHub!
    echo ====================================================
    echo Next step for Render worldwide access:
    echo 1. Go to https://dashboard.render.com
    echo 2. Click "New +" -> "Web Service"
    echo 3. Select this GitHub repository
    echo 4. Render will auto-deploy your app worldwide!
    echo ====================================================
)

echo.
pause
