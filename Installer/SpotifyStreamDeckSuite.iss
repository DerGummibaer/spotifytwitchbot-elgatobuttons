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
;
; SILENT UPDATE SUPPORT: this script detects an existing install (by
; checking for SpotifyService\.env) and skips the credential wizard pages
; entirely on update, preserving existing .env files and only registering
; whichever components were already present. This allows the tray icon's
; "Check for updates" to download and run this installer with
; /VERYSILENT /SUPPRESSMSGBOXES /NORESTART with zero user interaction.
;
; KNOWN GAP: the new .streamDeckPlugin file IS copied to {app} on a silent
; update (via [Files], which always runs), but it is NOT auto-installed
; into Stream Deck itself, since the [Run] entry that opens it has the
; skipifsilent flag (intentional -- a Stream Deck plugin install can show
; its own prompts that we can't suppress). After a silent auto-update,
; the Stream Deck plugin will keep running its old version until the user
; manually double-clicks the new .streamDeckPlugin file in the install
; folder, or reinstalls fresh. Worth fixing properly if plugin-side
; changes become frequent; not addressed here.

#define MyAppName "Spotify Stream Deck Suite"

; Read the version number from spotify-service/version.ini at compile
; time, rather than maintaining a separate hardcoded copy here that could
; drift out of sync. version.ini is kept in sync with version.py
; automatically by rebuild-all.bat, which prompts for a version number
; once and writes it to both files.
;
; NOTE: an earlier attempt tried parsing version.py directly line-by-line
; using FileOpen/FileRead inside a #for loop with a #sub callback. That
; approach hit repeated, hard-to-diagnose ISPP semantics issues (loop
; variable declaration order, ambiguous first-iteration timing, unclear
; reassignment semantics inside #for step expressions) across several
; real compile attempts and was abandoned in favor of this much simpler
; ReadIni-based approach, which is a single function call with no loop.
#define VersionIniPath SourcePath + "..\spotify service\version.ini"
#if FileExists(VersionIniPath)
  #define MyAppVersion ReadIni(VersionIniPath, "Version", "Number")
  #if MyAppVersion == ""
    #error version.ini was found but its [Version] section has no Number key -- expected something like: [Version]{break}Number=1.1.0
  #endif
#else
  #error Could not find version.ini at the expected path -- check VersionIniPath above matches your folder layout, or run rebuild-all.bat which keeps it in sync with version.py
#endif

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
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SpotifyStreamDeckSuiteSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; No admin required -- AppData is fully writable by the current user,
; which also means the service can write logs there without a UAC issue.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; -- Spotify service (always required) --
Source: "payload\SpotifyService\*"; DestDir: "{app}\SpotifyService"; Flags: ignoreversion recursesubdirs createallsubdirs

; -- Twitch bot (optional component, see [Components] below) --
Source: "payload\TwitchMusicBot\*"; DestDir: "{app}\TwitchMusicBot"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: twitchbot

; -- Command alias config template, staged under a different name so it
;    never silently overwrites a real command_aliases.txt the user has
;    already edited. [Code]'s DeployAliasTemplateIfMissing below copies
;    it to the real filename only the first time, when no real file
;    exists yet -- giving the convenience of having it show up out of
;    the box, without ever clobbering live edits on a later update. --
Source: "..\twitch-music-bot\command_aliases.txt.example"; DestDir: "{app}\TwitchMusicBot"; DestName: "command_aliases.txt.example"; Flags: ignoreversion; Components: twitchbot

; -- Convenience script to restart the bot after editing config (e.g.
;    command_aliases.txt) -- always safe to overwrite since it's not
;    user-editable config itself, just a fixed helper script. --
Source: "..\twitch-music-bot\restart-bot.bat"; DestDir: "{app}\TwitchMusicBot"; Flags: ignoreversion; Components: twitchbot

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
; Autostart via the Startup folder rather than Task Scheduler -- on at
; least some Windows configurations, schtasks.exe denies even per-user
; /SC ONLOGON task creation without elevation, which conflicts with this
; installer's no-admin design. A Startup folder shortcut needs no
; elevation at all and is removed automatically on uninstall, same as
; any other icon in this section.
Name: "{userstartup}\Spotify Stream Deck Service"; Filename: "{app}\SpotifyService\{#SpotifyServiceExeName}"; WorkingDir: "{app}\SpotifyService"

[Code]
var
  SpotifyPage: TInputQueryWizardPage;
  TwitchPage: TInputQueryWizardPage;
  ComponentsAdjustedForUpdate: Boolean;

function SpotifyEnvExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\SpotifyService\.env'));
end;

function TwitchBotWasInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\TwitchMusicBot\.env'));
end;

{ IsUpdate is computed fresh every time it's called, rather than cached in
  a variable set once during InitializeWizard -- the app directory constant
  has no value yet inside InitializeWizard (it only becomes valid once the
  wizard reaches or passes the directory selection page, wpSelectDir), so
  caching it there raised "attempt to expand the app constant before it
  was initialized". Every actual call site below (ShouldSkipPage for our
  pages, NextButtonClick, the env writers, CurStepChanged) only ever runs
  after wpSelectDir has been passed, so the app directory is reliably set
  by then. }
function IsUpdate: Boolean;
begin
  Result := SpotifyEnvExists;
end;

procedure InitializeWizard;
begin
  SpotifyPage := CreateInputQueryPage(wpSelectComponents,
    'Spotify connection',
    'Connect your own Spotify app',
    'Each user needs their own Spotify app, free to create, so no shared ' +
    'credentials or rate limits are involved.'#13#10#13#10 +
    'Open https://developer.spotify.com/dashboard, create an app, and add ' +
    'http://127.0.0.1:8888/callback as a Redirect URI. Then paste the ' +
    'Client ID below (the Client Secret is not needed).');
  SpotifyPage.Add('Spotify Client ID:', False);

  TwitchPage := CreateInputQueryPage(SpotifyPage.ID,
    'Twitch connection',
    'Connect your Twitch bot account',
    'Get a token from https://twitchtokengenerator.com (choose "Bot Chat ' +
    'Token") and paste it below, without the "oauth:" prefix.');
  TwitchPage.Add('Twitch OAuth token:', True);
  TwitchPage.Add('Twitch refresh token:', True);
  TwitchPage.Add('Twitch client ID (from twitchtokengenerator.com):', False);
  TwitchPage.Add('Twitch bot account username:', False);
  TwitchPage.Add('Your channel name (lowercase):', False);
  TwitchPage.Add('Your own Twitch username (broadcaster):', False);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { On a silent update, Inno Setup falls back to the [Types] default
    component selection rather than remembering what was previously
    installed -- without this, a silent re-run could silently install
    the Twitch bot for someone who originally chose not to (since
    "full" includes it by default), or silently remove it for someone
    who has it. Force the selection to match what's actually on disk,
    the first time we reach wpSelectComponents (the page itself, after
    which the app directory is certainly valid -- this page comes after
    wpSelectDir). }
  if (CurPageID = wpSelectComponents) and (not ComponentsAdjustedForUpdate) then
  begin
    ComponentsAdjustedForUpdate := True;
    if IsUpdate() then
    begin
      if TwitchBotWasInstalled then
        WizardSelectComponents('twitchbot')
      else
        WizardSelectComponents('!twitchbot');
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  { Check PageID membership first, before ever calling IsUpdate() --
    ShouldSkipPage is called by Inno Setup for every single wizard page,
    including wpSelectDir itself, well before the user has reached or
    passed it. IsUpdate() expands the app directory constant, which has
    no value until wpSelectDir is passed, so calling it unconditionally
    here (even behind an "and") crashed with "attempt to expand the app
    constant before it was initialized" the moment Setup evaluated this
    function for wpSelectDir on the way there. }
  if (PageID = SpotifyPage.ID) or (PageID = TwitchPage.ID) then
  begin
    if IsUpdate() then
    begin
      Result := True;
      exit;
    end;
  end;
  if (PageID = TwitchPage.ID) and (not IsComponentSelected('twitchbot')) then
    Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  { Same ordering issue as ShouldSkipPage above: NextButtonClick fires for
    every page's Next button, including wpWelcome and wpLicense, which
    come before wpSelectDir -- calling IsUpdate() unconditionally here
    crashed for the same reason. Only check it once CurPageID is
    confirmed to be one of our own pages, which by construction never
    appear before wpSelectDir has already been passed. }
  if (CurPageID = SpotifyPage.ID) or (CurPageID = TwitchPage.ID) then
  begin
    if IsUpdate() then
      exit;
  end;
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
         (Trim(TwitchPage.Values[2]) = '') or (Trim(TwitchPage.Values[3]) = '') or
         (Trim(TwitchPage.Values[4]) = '') or (Trim(TwitchPage.Values[5]) = '') then
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
  if FileExists(EnvPath) then
    exit; { update -- keep the user's existing credentials untouched }
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
  if FileExists(EnvPath) then
    exit; { update -- keep the user's existing credentials untouched }
  Content :=
    '# Generated by the installer.' + #13#10 +
    'TWITCH_OAUTH_TOKEN=' + TwitchPage.Values[0] + #13#10 +
    'TWITCH_REFRESH_TOKEN=' + TwitchPage.Values[1] + #13#10 +
    'TWITCH_CLIENT_ID=' + TwitchPage.Values[2] + #13#10 +
    'TWITCH_BOT_USERNAME=' + TwitchPage.Values[3] + #13#10 +
    'TWITCH_CHANNEL=' + Lowercase(TwitchPage.Values[4]) + #13#10 +
    'TWITCH_BROADCASTER_USERNAME=' + Lowercase(TwitchPage.Values[5]) + #13#10 +
    'SERVICE_HOST=127.0.0.1' + #13#10 +
    'SERVICE_PORT=9876' + #13#10;
  SaveStringToFile(EnvPath, Content, False);
end;

procedure DeployAliasTemplateIfMissing;
var
  RealPath: String;
  TemplatePath: String;
begin
  { Only relevant if the Twitch bot component is actually installed --
    the Files section above only stages the template when Components:
    twitchbot is selected, so the template file genuinely does not
    exist otherwise. }
  if not IsComponentSelected('twitchbot') then
    exit;

  RealPath := ExpandConstant('{app}\TwitchMusicBot\command_aliases.txt');
  TemplatePath := ExpandConstant('{app}\TwitchMusicBot\command_aliases.txt.example');

  { Never overwrite a real file the user may have already edited --
    this is the entire reason the template is staged under a different
    name in [Files] rather than written directly as command_aliases.txt:
    so a silent update can never clobber live alias edits. }
  if FileExists(RealPath) then
    exit;

  if FileExists(TemplatePath) then
    FileCopy(TemplatePath, RealPath, False);
end;

procedure RelaunchTwitchBotIfWasRunning;
var
  ResultCode: Integer;
  MarkerPath: String;
  BotExePath: String;
begin
  { The tray icon's silent-update flow stops TwitchMusicBot.exe before
    handing off to this installer, since its exe also needs to be
    unlocked for the [Files] copy step below (same reason
    SpotifyService.exe needs to be stopped first -- a locked exe gets
    silently skipped during file copy, with no error shown anywhere).
    If the bot WAS running, the tray process -- which has no other way
    to communicate with this separate installer process -- writes a
    marker file we check for here, so the bot comes back automatically
    after a silent update instead of silently staying down until the
    user notices and manually restarts OBS or the bot itself. }
  MarkerPath := ExpandConstant('{app}\TwitchMusicBot\_was_running_before_update');
  if not FileExists(MarkerPath) then
    exit;

  DeleteFile(MarkerPath);

  if not IsComponentSelected('twitchbot') then
    exit;

  BotExePath := ExpandConstant('{app}\TwitchMusicBot\{#TwitchBotExeName}');
  if FileExists(BotExePath) then
    Exec(BotExePath, '', '', SW_HIDE, ewNoWait, ResultCode);
end;

procedure LaunchSpotifyAuth;
var
  ResultCode: Integer;
  ExePath: String;
begin
  ExePath := ExpandConstant('{app}\SpotifyService\{#SpotifyServiceExeName}');

  if IsUpdate() or WizardSilent then
  begin
    { Updating an existing install (or, as a safety net, any genuinely
      silent run): the user already has a cached Spotify token and either
      doesn't need to re-authorize, or isn't present to click a dialog.
      Critically, this path must never show a blocking MsgBox -- a silent
      auto-update has nobody present to click OK, and a blocking dialog
      would hang it forever. }
    Exec(ExePath, '', '', SW_HIDE, ewNoWait, ResultCode);
    exit;
  end;

  { Important: SpotifyService.exe is the actual long-running service --
    it does NOT exit on its own. SpotifyController's __init__ triggers a
    one-time browser login automatically on first run (when no cached
    token exists yet), then the service keeps running afterwards exactly
    as it will every time going forward. We launch it with ewNoWait
    (never wait for it to finish, since it's not supposed to) and just
    give the user time to complete the browser flow before moving on.
    This MsgBox path only runs on a genuine first install, never on a
    silent update, since IsUpdate is checked above first. }
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
    begin
      WriteTwitchBotEnv;
      DeployAliasTemplateIfMissing;
    end;
    LaunchSpotifyAuth;
    RelaunchTwitchBotIfWasRunning;
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

; No [UninstallRun] section needed -- the Startup folder shortcut in
; [Icons] above is automatically removed on uninstall, the same as any
; other icon, with no extra code required.
