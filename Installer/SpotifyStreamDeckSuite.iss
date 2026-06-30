; Spotify Stream Deck Suite -- installer
; Bundles the Spotify service, the optional Twitch bot, and guides the
; user through linking Spotify, setting up autostart, and installing
; the Stream Deck plugin.
;
; BEFORE COMPILING, you must have already built:
;   - dist\SpotifyService\   (from the spotify-service project's PyInstaller build)
;   - dist\TwitchMusicBot\   (from the twitch-music-bot project's PyInstaller build)
;   - com.leon.spotifycontrol.streamDeckPlugin (from the spotify-streamdeck project)
; and placed copies of each inside this installer project's "payload" folder
; (see payload\README.txt for the exact expected layout).

#define MyAppName "Spotify Stream Deck Suite"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Leon"
#define MyAppURL "https://github.com/"
#define SpotifyServiceExeName "SpotifyService.exe"
#define TwitchBotExeName "TwitchMusicBot.exe"
#define StreamDeckPluginFile "com.leon.spotifycontrol.streamDeckPlugin"

[Setup]
AppId={{B1B3F6B0-6C2A-4B9E-9C1A-7F2D5E8A9C10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SpotifyStreamDeckSuiteSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Task Scheduler registration needs admin rights -- see [Code] section.
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; -- Spotify service (always required) --
Source: "payload\SpotifyService\*"; DestDir: "{app}\SpotifyService"; Flags: ignoreversion recursesubdirs createallsubdirs

; -- Twitch bot (optional component, see [Components] below) --
Source: "payload\TwitchMusicBot\*"; DestDir: "{app}\TwitchMusicBot"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: twitchbot

; -- Stream Deck plugin file, just staged here; actually installed by
;    double-clicking it, which we trigger automatically post-install --
Source: "payload\{#StreamDeckPluginFile}"; DestDir: "{app}"; Flags: ignoreversion

[Components]
Name: "twitchbot"; Description: "Twitch chat bot (optional -- !sr, !vol, !skip, !remove, !sq commands)"; Types: full custom

[Types]
Name: "full"; Description: "Full install (Spotify service + Twitch bot)"
Name: "custom"; Description: "Custom"; Flags: iscustom

[Icons]
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Code]
var
  SpotifyPage: TInputQueryWizardPage;
  TwitchPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  { Page 1: Spotify app credentials -- always shown, since the service
    is required regardless of whether the Twitch bot is installed. }
  SpotifyPage := CreateInputQueryPage(wpSelectComponents,
    'Spotify connection',
    'Connect your own Spotify app',
    'Each user needs their own Spotify app, free to create, so no shared ' +
    'credentials or rate limits are involved.'#13#10#13#10 +
    'Open https://developer.spotify.com/dashboard, create an app, and add ' +
    'http://127.0.0.1:8888/callback as a Redirect URI. Then paste the ' +
    'Client ID below (the Client Secret is not needed).');
  SpotifyPage.Add('Spotify Client ID:', False);

  { Page 2: Twitch credentials -- only relevant if the Twitch bot
    component is selected; we still create it unconditionally here, but
    skip showing it via ShouldSkipPage below if the component is unchecked. }
  TwitchPage := CreateInputQueryPage(SpotifyPage.ID,
    'Twitch connection',
    'Connect your Twitch bot account',
    'Get a token from https://twitchtokengenerator.com (choose "Bot Chat ' +
    'Token") and paste it below, without the "oauth:" prefix.');
  TwitchPage.Add('Twitch OAuth token:', True);
  TwitchPage.Add('Twitch bot account username:', False);
  TwitchPage.Add('Your channel name (lowercase):', False);
  TwitchPage.Add('Your own Twitch username (broadcaster):', False);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = TwitchPage.ID) and (not IsComponentSelected('twitchbot')) then
    Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = SpotifyPage.ID then
  begin
    if Trim(SpotifyPage.Values[0]) = '' then
    begin
      MsgBox('Please enter your Spotify Client ID before continuing.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = TwitchPage.ID then
  begin
    if IsComponentSelected('twitchbot') then
    begin
      if (Trim(TwitchPage.Values[0]) = '') or (Trim(TwitchPage.Values[1]) = '') or
         (Trim(TwitchPage.Values[2]) = '') or (Trim(TwitchPage.Values[3]) = '') then
      begin
        MsgBox('Please fill in all four Twitch fields before continuing.', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

procedure WriteSpotifyServiceEnv;
var
  EnvPath: String;
  Content: String;
begin
  EnvPath := ExpandConstant('{app}\SpotifyService\.env');
  Content :=
    '# Generated by the installer.' + #13#10 +
    'SPOTIFY_CLIENT_ID=' + SpotifyPage.Values[0] + #13#10 +
    'SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback' + #13#10 +
    'CONTROL_HOST=127.0.0.1' + #13#10 +
    'CONTROL_PORT=9876' + #13#10;
  SaveStringToFile(EnvPath, Content, False);
end;

procedure WriteTwitchBotEnv;
var
  EnvPath: String;
  Content: String;
begin
  EnvPath := ExpandConstant('{app}\TwitchMusicBot\.env');
  Content :=
    '# Generated by the installer.' + #13#10 +
    'TWITCH_OAUTH_TOKEN=' + TwitchPage.Values[0] + #13#10 +
    'TWITCH_BOT_USERNAME=' + TwitchPage.Values[1] + #13#10 +
    'TWITCH_CHANNEL=' + Lowercase(TwitchPage.Values[2]) + #13#10 +
    'TWITCH_BROADCASTER_USERNAME=' + Lowercase(TwitchPage.Values[3]) + #13#10 +
    'SERVICE_HOST=127.0.0.1' + #13#10 +
    'SERVICE_PORT=9876' + #13#10;
  SaveStringToFile(EnvPath, Content, False);
end;

procedure RegisterSpotifyServiceTask;
var
  ResultCode: Integer;
  ExePath: String;
  TaskCommand: String;
begin
  ExePath := ExpandConstant('{app}\SpotifyService\{#SpotifyServiceExeName}');
  { /F overwrites a task of the same name if one already exists, so re-running
    the installer to upgrade doesn't fail on a duplicate. }
  TaskCommand := '/Create /TN "SpotifyStreamDeckService" /TR "' + ExePath + '" /SC ONLOGON /RL LIMITED /F';
  { schtasks.exe run via [Run] entries fails with Access Denied even when
    the installer itself is elevated -- Exec() here runs it correctly
    elevated instead. }
  if not Exec(ExpandConstant('{sys}\schtasks.exe'), TaskCommand, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Could not register the Spotify service to start automatically. You can set this up manually later -- see the README.', mbError, MB_OK);
  end
  else if ResultCode <> 0 then
  begin
    MsgBox('Task Scheduler reported an error (code ' + IntToStr(ResultCode) + ') while registering the Spotify service to start automatically. You can set this up manually later -- see the README.', mbError, MB_OK);
  end;
end;

procedure LaunchSpotifyAuth;
var
  ResultCode: Integer;
  ExePath: String;
begin
  { Important: SpotifyService.exe is the actual long-running service --
    it does NOT exit on its own. SpotifyController's __init__ triggers a
    one-time browser login automatically on first run (when no cached
    token exists yet), then the service keeps running afterwards exactly
    as it will every time going forward. We launch it with ewNoWait
    (never wait for it to finish, since it's not supposed to) and just
    give the user time to complete the browser flow before moving on. }
  ExePath := ExpandConstant('{app}\SpotifyService\{#SpotifyServiceExeName}');
  MsgBox('Next, the Spotify service will start in the background, and a ' +
         'browser window should open so you can log in and authorize this ' +
         'app with your Spotify account. Click OK to continue, then approve ' +
         'access in the browser. The service will keep running afterwards -- ' +
         'that''s expected, it''s meant to stay running.', mbInformation, MB_OK);
  Exec(ExePath, '', '', SW_SHOW, ewNoWait, ResultCode);
  Sleep(5000);
  MsgBox('If a browser window opened and you approved access, Spotify is now ' +
         'linked, and the service is already running in the background. If no ' +
         'browser window appeared, check ' +
         ExpandConstant('{app}\SpotifyService\logs\spotify_service.log') +
         ' for what happened, or try running SpotifyService.exe manually.',
         mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WriteSpotifyServiceEnv;
    if IsComponentSelected('twitchbot') then
      WriteTwitchBotEnv;
    RegisterSpotifyServiceTask;
    LaunchSpotifyAuth;
  end;
end;

[Run]
; Open the Stream Deck plugin file so the OS handles installing it --
; this is the documented way to install a packaged plugin, equivalent to
; the user double-clicking it themselves.
Filename: "{app}\{#StreamDeckPluginFile}"; Flags: shellexec postinstall skipifsilent; Description: "Install the Stream Deck plugin now"
; Guided manual step: OBS Autostarter can't be silently installed since
; it's a third-party OBS plugin, not something this installer can ship
; or modify OBS's plugin folder for safely. Open its download page instead.
Filename: "https://obsproject.com/forum/resources/autostarter.2083/"; Flags: shellexec postinstall skipifsilent unchecked; Description: "Open the OBS Autostarter page (only needed if you installed the Twitch bot and want it tied to OBS)"

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""SpotifyStreamDeckService"" /F"; Flags: runhidden; RunOnceId: "RemoveSpotifyServiceTask"
