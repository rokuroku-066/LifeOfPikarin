@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Windows 開発環境セットアップ用スクリプト
REM - .NET 8 SDK を確認し、未導入なら winget からインストールを試みます。
REM - Unity Hub / Unity 6.x LTS (推奨: 6.3 LTS) の導入状況を確認し、見つからなければ案内します。
REM - ソリューションの復元とテスト実行を行い、開発前に動作確認します。

set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"

REM ルート確認
if not exist "Terrarium.sln" (
    echo [ERROR] Terrarium.sln が見つかりません。リポジトリのルートで実行してください。
    exit /b 1
)

echo === .NET 8 SDK の確認 ===
where dotnet >nul 2>nul
if errorlevel 1 (
    echo [INFO] dotnet コマンドが見つかりませんでした。
    set NEED_DOTNET=1
) else (
    for /f "tokens=*" %%v in ('dotnet --list-sdks ^| findstr "^8\."') do (
        set FOUND_SDK=%%v
    )
    if not defined FOUND_SDK (
        echo [INFO] .NET 8 SDK が見つかりませんでした。
        set NEED_DOTNET=1
    ) else (
        echo [OK] .NET 8 SDK が見つかりました: !FOUND_SDK!
    )
)

echo ---
echo === Unity Hub / Unity Editor 6.x LTS の確認 ===
set "UNITY_HUB_EXE="
for %%p in ("%ProgramFiles%" "%ProgramFiles(x86)%") do (
    if exist "%%~p\Unity Hub\Unity Hub.exe" (
        set "UNITY_HUB_EXE=%%~p\Unity Hub\Unity Hub.exe"
    )
)

if defined UNITY_HUB_EXE (
    echo [OK] Unity Hub が見つかりました: !UNITY_HUB_EXE!
) else (
    echo [INFO] Unity Hub が見つかりませんでした。winget でのインストールを試みます。
    where winget >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] winget が見つからないため、Unity Hub を自動インストールできません。
        echo        Microsoft Store の App Installer を導入後、以下のコマンドを実行してください:
        echo        winget install --id Unity.UnityHub -e --accept-package-agreements --accept-source-agreements
        exit /b 1
    )
    winget install --id Unity.UnityHub -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Unity Hub のインストールに失敗しました。手動でセットアップしてください。
        exit /b 1
    )
    if exist "%ProgramFiles%\Unity Hub\Unity Hub.exe" (
        set "UNITY_HUB_EXE=%ProgramFiles%\Unity Hub\Unity Hub.exe"
    ) else if exist "%ProgramFiles(x86)%\Unity Hub\Unity Hub.exe" (
        set "UNITY_HUB_EXE=%ProgramFiles(x86)%\Unity Hub\Unity Hub.exe"
    )
    if defined UNITY_HUB_EXE (
        echo [OK] Unity Hub のインストールが完了しました: !UNITY_HUB_EXE!
    ) else (
        echo [WARN] Unity Hub のパスが自動検出できませんでした。スタートメニューから一度起動してパスを確認してください。
    )
)

set "UNITY_EDITOR_FOUND="
for %%p in ("%ProgramFiles%" "%ProgramFiles(x86)%") do (
    for /d %%e in ("%%~p\Unity\Hub\Editor\6.*") do (
        if exist "%%~e\Editor\Unity.exe" (
            set "UNITY_EDITOR_FOUND=%%~e\Editor\Unity.exe"
        )
    )
)

if defined UNITY_EDITOR_FOUND (
    echo [OK] Unity 6.x LTS Editor を検出しました: !UNITY_EDITOR_FOUND!
) else (
    echo [INFO] Unity 6.x LTS Editor が見つかりませんでした。
    echo        Unity Hub から **Unity 6.3 LTS** をインストールしてください。
    echo        推奨モジュール: "Windows Build Support (IL2CPP)" と "Microsoft Visual Studio" または VS ビルドツール。
    if defined UNITY_HUB_EXE (
        echo        例: "!UNITY_HUB_EXE!" -- --headless editors install --version 6.3.0f1 --module windows-il2cpp
    )
)

set "DOTNET_CMD=dotnet"

if defined NEED_DOTNET (
    echo ---
    echo .NET 8 SDK を winget からインストールします。管理者権限が求められる場合があります。
    where winget >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] winget が見つからないため、自動インストールできません。\
              Windows Update から App Installer を入れるか、公式手順で SDK を導入してください:
        echo https://dotnet.microsoft.com/ja-jp/download/dotnet/8.0
        exit /b 1
    )
    winget install --id Microsoft.DotNet.SDK.8 --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] .NET 8 SDK のインストールに失敗しました。
        exit /b 1
    )

    if exist "%ProgramFiles%\dotnet\dotnet.exe" (
        set "DOTNET_CMD=%ProgramFiles%\dotnet\dotnet.exe"
        set "PATH=%ProgramFiles%\dotnet;%PATH%"
    ) else if exist "%ProgramFiles(x86)%\dotnet\dotnet.exe" (
        set "DOTNET_CMD=%ProgramFiles(x86)%\dotnet\dotnet.exe"
        set "PATH=%ProgramFiles(x86)%\dotnet;%PATH%"
    )
)

echo ---
echo dotnet --info で SDK を確認します。
"%DOTNET_CMD%" --info
if errorlevel 1 (
    echo [ERROR] dotnet --info に失敗しました。
    exit /b 1
)

echo === NuGet 復元 ===
"%DOTNET_CMD%" restore Terrarium.sln
if errorlevel 1 (
    echo [ERROR] 依存関係の復元に失敗しました。
    exit /b 1
)

echo === シミュレーションテスト実行 ===
"%DOTNET_CMD%" test tests\SimTests\SimTests.csproj
if errorlevel 1 (
    echo [ERROR] テストが失敗しました。詳細を確認してください。
    exit /b 1
)

echo === 完了 ===
echo 開発環境のセットアップが完了しました。Unity 6.3 LTS もインストールしてプロジェクトを開いてください。

popd
exit /b 0
