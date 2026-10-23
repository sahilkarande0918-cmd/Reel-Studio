<#
Moves Claude Code's data folder (%USERPROFILE%\.claude: sessions, memories, settings, skills, plugins,
hooks, file history) to D: and leaves a directory junction at the old path, so every tool and every
absolute path stored in Claude's config keeps working unchanged. Files are copied byte for byte
(SHA-256 checked); nothing is deleted. The original folder is kept on C: as
.claude.pre-migration-<timestamp> until you delete it yourself.

Run from a normal PowerShell window with ALL Claude apps closed (Desktop incl. tray icon, every
`claude` terminal, VS Code / JetBrains windows using Claude):
  powershell -ExecutionPolicy Bypass -File migrate-claude-storage.ps1 -DryRun     # checks only
  powershell -ExecutionPolicy Bypass -File migrate-claude-storage.ps1             # migrate
  powershell -ExecutionPolicy Bypass -File migrate-claude-storage.ps1 -Rollback   # undo
#>
[CmdletBinding()]
param(
  [string]$Source = (Join-Path $env:USERPROFILE '.claude'),
  [string]$Dest = 'D:\ClaudeStorage\.claude',
  [switch]$DryRun,
  [switch]$Rollback,
  [switch]$SkipProcessCheck  # only for rehearsals on a test folder, never for the real one
)
$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$root = Split-Path $Dest -Parent
$statePath = Join-Path $root 'migration-state.json'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$log = Join-Path $root "migration-$stamp.log"

function Log($m) { $line = "$(Get-Date -Format s)  $m"; Write-Host $line; Add-Content -LiteralPath $log -Value $line }
function Fail($m) { Log "STOPPED: $m"; Log "Log file: $log"; exit 1 }

function Get-ClaudeProcesses {
  $p = @(Get-Process -Name claude -ErrorAction SilentlyContinue)
  $n = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'claude' })
  $p.Count + $n.Count
}

function Assert-ClaudeClosed {
  if ($SkipProcessCheck) { return }
  $c = Get-ClaudeProcesses
  if ($c -gt 0) {
    Fail "$c Claude process(es) still running. Quit Claude Desktop (also from the tray), close every Claude Code terminal and IDE window, then run again. Nothing was changed."
  }
}

function Test-Link($path) {
  (Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)
}

# relative path -> "length|sha256" for every file
function Get-Manifest($dir) {
  $base = (Get-Item -LiteralPath $dir -Force).FullName.TrimEnd('\')
  $m = @{}
  Get-ChildItem -LiteralPath $dir -Recurse -Force -File | ForEach-Object {
    $m[$_.FullName.Substring($base.Length + 1)] = '{0}|{1}' -f $_.Length, (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
  }
  $m
}

function Invoke-Robocopy($from, $to, [string[]]$extra) {
  & robocopy $from $to /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /NP /NFL /NDL "/LOG+:$log" @extra | Out-Null
  if ($LASTEXITCODE -ge 8) { Fail "robocopy failed with code $LASTEXITCODE (see log)." }
}

if ($Rollback) {
  if (-not (Test-Path -LiteralPath $statePath)) { Fail "No migration record at $statePath." }
  $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
  Assert-ClaudeClosed
  if (-not (Test-Link $state.Source)) { Fail "$($state.Source) is not a junction; nothing to roll back." }
  if (-not (Test-Path -LiteralPath $state.Backup)) { Fail "Original folder $($state.Backup) is missing; not touching anything." }
  Log "Removing the junction $($state.Source) (the D: copy is not touched)"
  & cmd /c rmdir "$($state.Source)"
  if (Test-Path -LiteralPath $state.Source) { Fail "Could not remove the junction." }
  Log "Copying files created or changed on D: since the migration back into the original folder (newer only)"
  Invoke-Robocopy $state.Dest $state.Backup @('/XO')
  Rename-Item -LiteralPath $state.Backup -NewName (Split-Path $state.Source -Leaf)
  Log "Rolled back. $($state.Source) is a normal folder again; the D: copy at $($state.Dest) is left in place."
  exit 0
}

# ---- preflight ----
Log "Source: $Source"
Log "Destination: $Dest"
if (-not (Test-Path -LiteralPath $Source)) { Fail "$Source not found." }
if (Test-Link $Source) { Fail "$Source is already a link to $((Get-Item -LiteralPath $Source -Force).Target). Already migrated?" }
if ((Test-Path -LiteralPath $Dest) -and (Get-ChildItem -LiteralPath $Dest -Force | Select-Object -First 1)) {
  Fail "$Dest already exists and is not empty. Refusing to overwrite it."
}
if (Get-ChildItem -LiteralPath $Source -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue) {
  Fail "Source contains links/junctions; move those by hand first."
}
$files = @(Get-ChildItem -LiteralPath $Source -Recurse -Force -File)
$bytes = ($files | Measure-Object Length -Sum).Sum
$free = (Get-PSDrive -Name $Dest.Substring(0, 1)).Free
$sessions = @($files | Where-Object { $_.Extension -eq '.jsonl' -and $_.FullName -like '*\projects\*' }).Count
Log ("Source: {0} files, {1:N2} GB, {2} session transcripts. Free on {3}: {4:N1} GB" -f $files.Count, ($bytes / 1GB), $sessions, $Dest.Substring(0, 2), ($free / 1GB))
if ($free -lt (2 * $bytes + 1GB)) { Fail 'Not enough free space on the destination drive.' }
$backup = Join-Path (Split-Path $Source -Parent) ((Split-Path $Source -Leaf) + ".pre-migration-$stamp")

if ($DryRun) {
  $c = Get-ClaudeProcesses
  if ($c -gt 0) { Log "WARNING: $c Claude process(es) running now; the real run will refuse until they are closed." }
  Log "DRY RUN OK. The real run will copy to $Dest, verify every file, rename the original to $backup and create a junction $Source -> $Dest. Nothing was changed."
  exit 0
}

Assert-ClaudeClosed

# ---- 1. private permissions on the destination root (D:\ is readable by all users by default) ----
$me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $root /inheritance:r /grant:r "*${me}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not set permissions on $root." }

# ---- 2. copy user-level config that lives outside .claude (stays live on C:, this is a backup) ----
$cfgBackup = Join-Path $root "user-config-backup-$stamp"
New-Item -ItemType Directory -Force -Path $cfgBackup | Out-Null
Get-ChildItem -LiteralPath (Split-Path $Source -Parent) -Force -File -Filter '.claude.json*' | Copy-Item -Destination $cfgBackup
Log "Backed up $((Get-ChildItem $cfgBackup -Force).Count) user config file(s) to $cfgBackup"

# ---- 3. hash, copy, verify ----
Log "Hashing source files"
$before = Get-Manifest $Source
Log "Copying (timestamps preserved)"
Invoke-Robocopy $Source $Dest @()
Log "Verifying every file (size + SHA-256)"
$after = Get-Manifest $Dest
$bad = @($before.Keys | Where-Object { $after[$_] -ne $before[$_] })
if ($bad.Count -gt 0) {
  $bad | Select-Object -First 20 | ForEach-Object { Log "  mismatch: $_" }
  Fail "$($bad.Count) file(s) differ. The original is untouched; delete $Dest and run again."
}
Log "Verified $($before.Count) files."

# ---- 4. switch: keep the original, link the old path to D: ----
Assert-ClaudeClosed
Rename-Item -LiteralPath $Source -NewName (Split-Path $backup -Leaf)
try {
  New-Item -ItemType Junction -Path $Source -Target $Dest | Out-Null
} catch {
  Rename-Item -LiteralPath $backup -NewName (Split-Path $Source -Leaf)
  Fail "Could not create the junction ($_). Original restored."
}
@{ Source = $Source; Dest = $Dest; Backup = $backup; Stamp = $stamp } | ConvertTo-Json | Set-Content -LiteralPath $statePath

# ---- 5. post-checks ----
$viaLink = @(Get-ChildItem -LiteralPath $Source -Recurse -Force -File).Count
if ($viaLink -ne $before.Count) { Fail "Junction shows $viaLink files, expected $($before.Count). Run with -Rollback." }
$probe = Join-Path $Source ".migration-probe-$stamp"
Set-Content -LiteralPath $probe -Value 'probe'
$landed = Test-Path -LiteralPath (Join-Path $Dest (Split-Path $probe -Leaf))
Remove-Item -LiteralPath $probe
if (-not $landed) { Fail 'A file written through the junction did not land on D:. Run with -Rollback.' }

Log "DONE. $Source -> $Dest ($viaLink files; new writes land on D:)."
Log "Original kept at $backup (delete it only after you have checked Claude works)."
Log "Undo any time with: -Rollback"
