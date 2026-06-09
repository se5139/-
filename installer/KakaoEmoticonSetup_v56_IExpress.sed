[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AppLaunched%
UserQuietInstCmd=%AppLaunched%
SourceFiles=SourceFiles
[Strings]
InstallPrompt=This fallback EXE extracts the v56 package and runs 1_INSTALL_NOW.bat.
DisplayLicense=
FinishMessage=Kakao Emoticon v56 fallback package launched.
TargetName=installer\Output\KakaoEmoticonSetup_v56_fallback.exe
FriendlyName=Kakao Emoticon v56 Fallback Setup
AppLaunched=1_INSTALL_NOW.bat
PostInstallCmd=<None>
FILE0=1_INSTALL_NOW.bat
[SourceFiles]
SourceFiles0=..
[SourceFiles0]
%FILE0%=
