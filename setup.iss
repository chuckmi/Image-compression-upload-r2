[Setup]
AppName=Panda图片压缩工具
AppVersion=1.0
DefaultDirName={pf}\Panda图片压缩工具
DefaultGroupName=Panda图片压缩工具
OutputDir=output
OutputBaseFilenamePanda图片压缩工具_安装程序
SetupIconFile=icon.png
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\Panda图片压缩工具.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Panda图片压缩工具"; Filename: "{app}\Panda图片压缩工具.exe"
Name: "{commondesktop}\Panda图片压缩工具"; Filename: "{app}\Panda图片压缩工具.exe" 