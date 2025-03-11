[Setup]
AppName=盼趣图片压缩工具
AppVersion=1.0
DefaultDirName={pf}\盼趣图片压缩工具
DefaultGroupName=盼趣图片压缩工具
OutputDir=output
OutputBaseFilename=盼趣图片压缩工具_安装程序
SetupIconFile=icon.png
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\盼趣图片压缩工具.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\盼趣图片压缩工具"; Filename: "{app}\盼趣图片压缩工具.exe"
Name: "{commondesktop}\盼趣图片压缩工具"; Filename: "{app}\盼趣图片压缩工具.exe" 