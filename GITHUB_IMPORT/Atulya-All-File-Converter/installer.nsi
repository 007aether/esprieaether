; Atulya All File Converter - Windows System Installer Script (NSIS)
!include "MUI2.nsh"
!include "FileFunc.nsh"

; General Definitions
Name "Atulya File Converter"
OutFile "dist\atulya-convert-installer.exe"
InstallDir "$PROGRAMFILES64\Atulya File Converter"
InstallDirRegKey HKLM "Software\Atulya\FileConverter" "Install_Dir"
RequestExecutionLevel admin

; Interface Configuration
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installation Section
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    
    ; Install compiled binary and support files
    File "dist\atulya-convert.exe"
    File /nonfatal "LICENSE"
    File /nonfatal "README.md"
    
    ; Write the installation path into the registry
    WriteRegStr HKLM "Software\Atulya\FileConverter" "Install_Dir" "$INSTDIR"
    
    ; Windows File Explorer Context Menu Integration (Right click on any file -> Convert with Atulya)
    WriteRegStr HKCR "*\shell\AtulyaConvert" "" "Convert with Atulya"
    WriteRegStr HKCR "*\shell\AtulyaConvert" "Icon" "$INSTDIR\atulya-convert.exe"
    WriteRegStr HKCR "*\shell\AtulyaConvert\command" "" '"$INSTDIR\atulya-convert.exe" "%1"'

    ; Add to System PATH
    EnVar::AddValue "Path" "$INSTDIR"
    
    ; Write Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter" "DisplayName" "Atulya File Converter"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter" "DisplayIcon" "$INSTDIR\atulya-convert.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter" "Publisher" "Atulya AI"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter" "DisplayVersion" "1.0.0"

    ; Create Shortcuts
    CreateDirectory "$SMPROGRAMS\Atulya File Converter"
    CreateShortcut "$SMPROGRAMS\Atulya File Converter\Atulya File Converter.lnk" "$INSTDIR\atulya-convert.exe" "--help"
    CreateShortcut "$SMPROGRAMS\Atulya File Converter\Atulya Converter Web Studio.lnk" "$INSTDIR\atulya-convert.exe" "serve"
    CreateShortcut "$SMPROGRAMS\Atulya File Converter\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortcut "$DESKTOP\Atulya File Converter.lnk" "$INSTDIR\atulya-convert.exe" "serve"
SectionEnd

; Uninstallation Section
Section "Uninstall"
    ; Remove Context Menu
    DeleteRegKey HKCR "*\shell\AtulyaConvert"
    
    ; Remove System PATH
    EnVar::DeleteValue "Path" "$INSTDIR"
    
    ; Remove Registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtulyaFileConverter"
    DeleteRegKey HKLM "Software\Atulya\FileConverter"
    
    ; Remove files and shortcuts
    Delete "$INSTDIR\atulya-convert.exe"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\README.md"
    
    Delete "$SMPROGRAMS\Atulya File Converter\*.*"
    RMDir "$SMPROGRAMS\Atulya File Converter"
    Delete "$DESKTOP\Atulya File Converter.lnk"
    
    RMDir "$INSTDIR"
SectionEnd
