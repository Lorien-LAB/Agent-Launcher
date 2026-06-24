@echo off
echo Agent Launcher (C# WPF)
echo.

where dotnet >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: .NET 8 SDK is required. Install from https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

cd /d "%~dp0"
dotnet run --project AgentLauncher.csproj
