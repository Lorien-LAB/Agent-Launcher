@echo off
echo Building Agent Launcher (C# WPF) as standalone .exe...
echo.

where dotnet >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: .NET 8 SDK is required.
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/2] Restoring packages...
dotnet restore AgentLauncher.csproj
if %ERRORLEVEL% NEQ 0 goto :error

echo [2/2] Publishing single-file executable...
dotnet publish AgentLauncher.csproj -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true -o publish
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo SUCCESS: publish\AgentLauncher.exe (~5 MB)
echo.
pause
exit /b 0

:error
echo.
echo BUILD FAILED
pause
exit /b 1
