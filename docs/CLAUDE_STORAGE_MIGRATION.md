# Claude storage migration C: → D: (run and verified 2026-10-24)

Script: `scripts/claude-storage/migrate-claude-storage.ps1`. It moves Claude Code's folder to D: with
zero deletion and leaves a junction at the old path. Status: **done; verified (results below). The C: original
`C:\Users\Sahil\.claude.pre-migration-20261024-052725` and `D:\ClaudeStorage\user-config-backup-20261024-052725` are
kept until the owner approves deleting them.**

## Verification results (after restart, 2026-10-24 05:28–05:30)
- `C:\Users\Sahil\.claude` is a Junction → `D:\ClaudeStorage\.claude`; log `migration-20261024-052725.log` ends DONE
  (3,551 files SHA-256 verified by the script).
- Independent re-check, original vs D: 3,549 identical, 1 updated since (this session's transcript), 1 absent:
  `backups\.claude.json.backup.1792797515976`, removed by Claude Code's own rotation (it keeps 5 config backups and
  wrote `…1792799969018` at 05:28:27). The file is still in the C: original.
- Transcripts: 18 on D: = 18 in the original. Tamrivo: `315673bf-…` 247,163,796 B and `b5e5b291-…` 249,074,920 B,
  identical sizes, + 3 memory files identical. Reel Studio 2.0 session `cb493782-…` resumed from D: and keeps growing there.
- New writes go to D: (transcript, `sessions\`, config backup, plugin cache, ponytail hook flag); 0 files written to the
  C: original since the switch.
- `settings.json` parses (keys unchanged + `cleanupPeriodDays: 3650` added); 13 skills present and loaded; plugin
  ponytail install path valid and its SessionStart hook ran; both marketplaces resolve; user MCP servers (stitch,
  motionsites) and project MCP (blender) configured; no config path points to a missing `.claude` folder;
  `.credentials.json` present (not read) and the session is signed in; `gh auth status` logged in as
  sahilkarande0918-cmd.
- Not checkable from inside a session: the `/resume` picker itself. The Reel Studio session was resumed by the app;
  Tamrivo's session files are intact where Claude looks for them; open `/resume` in `C:\dev\AnswerRank` once to confirm
  (resuming would append to that transcript, so it was not done here).

## What was measured (2026-10-24)
C: 446.8 GB used, **13.3 GB free**; D: 457.6 GB free. `CLAUDE_CONFIG_DIR` is not set anywhere.

| Path | Size | What it is | Migrated? |
|---|---|---|---|
| `%USERPROFILE%\.claude` | 1.10 GB, 3,555 files | All Claude Code data: `projects\` (18 session transcripts + memories, 0.81 GB), settings, skills, plugins, hooks, file-history, credentials | **Yes** (junction) |
| `%USERPROFILE%\.claude.json` (+ `.backup`) | 87 KB | User-level config (MCP servers, project list) | Backed up to D:, stays live on C: (a file can't be junctioned; no space gain) |
| `%APPDATA%\Claude` | 0.93 GB | Claude Desktop data: `claude-code\` binaries 0.55 GB (managed by the app), caches 0.33 GB, Desktop sessions/logs | No (small gain, the app manages it) |
| `%LOCALAPPDATA%\AnthropicClaude` | 2.06 GB | Desktop app install (3 versions) | No (program files, the updater manages them) |
| `%LOCALAPPDATA%\Claude`, `claude-cli-nodejs`, `Packages\Claude_*` | 0.04 GB | small state/caches | No |

**Moving Claude frees about 1.1 GB.** Claude is not what fills C:. Largest items (not touched, owner's call):
`AppData\Local\Docker` 24.9 GB + `wsl` 14.6 GB, `AppData\Local\Android` 18.1 GB + `.android` 11.6 GB + `.gradle` 7.3 GB,
`AppData\Local\reel-studio` 18.0 GB (engine data, models, venvs, renders), `npm-cache` 16.1 GB, `Downloads` 15.7 GB,
`.cache` 11.0 GB, `pip` cache 9.2 GB, `miniconda3` 7.2 GB, `.gemini` 7.0 GB, `.loopmatch-build` 6.6 GB, `.ollama` 5.6 GB.
Safe, reversible cleanups: `npm cache clean --force` (≈16 GB), `pip cache purge` (≈9 GB). Docker Desktop can move its
disk image to D: (Settings → Resources → Advanced → Disk image location).

## Projects (not moved)
- Reel Studio 2.0 (`C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`): 0.99 GB. Moving it gains little and would
  change the session key; **leave it**. The engine data (`AppData\Local\reel-studio`, 18 GB) is the real Reel Studio
  space user. Moving it means changing `DATA_DIR` and rebuilding both venvs (their paths are absolute); do that as a
  separate, planned task if needed.
- AnswerRank/Tamrivo (`C:\dev\AnswerRank`, branch `wip/phase-16`, remote `sahilkarande0918-cmd/AnswerRank`): 4.33 GB.
  **Not touched** (no files, remotes, Supabase, Vercel or env changes). Moving it is not recommended (small gain,
  path-keyed sessions). Its Claude data, `.claude\projects\C--dev-AnswerRank\` (sessions `315673bf-…` 247 MB and
  `b5e5b291-…` 249 MB + its subagent folder + 3 memory files), moves with the rest and is SHA-256 checked.

## Why a junction (not `CLAUDE_CONFIG_DIR`)
Claude's own config stores absolute paths into `C:\Users\Sahil\.claude` (`plugins\installed_plugins.json`,
`plugins\known_marketplaces.json`), and the Desktop app, IDE extensions and hooks look there too. A junction keeps
every one of those paths valid with no edits, no session-file rewrites and no change to project keys. Using both
mechanisms at once would split the data, so only the junction is used.

## What the script does
1. Refuses to run if any Claude process is open, if the source is already a link, if the destination is not empty,
   or if D: lacks 2× the space.
2. Makes `D:\ClaudeStorage` private (only you, SYSTEM, Administrators; D:\ is readable by all users by default).
3. Copies `.claude.json*` to `D:\ClaudeStorage\user-config-backup-<time>\`.
4. Hashes every file, copies with robocopy (timestamps kept, no `/MIR`, no deletes), re-hashes, stops on any mismatch.
5. Renames the original to `C:\Users\Sahil\.claude.pre-migration-<time>` (kept, nothing deleted), creates the junction
   `C:\Users\Sahil\.claude → D:\ClaudeStorage\.claude`, checks file count through the link and that a test write lands on D:.
6. Records `D:\ClaudeStorage\migration-state.json`; `-Rollback` removes only the link, copies anything new from D:
   back (newer files only) and restores the original name.

Rehearsed on 2026-10-24 (Windows PowerShell 5.1, 585-file copy of skills + fake sessions + unicode/hidden files):
dry run ✅, migrate ✅ (585/585 hashes, mtime and hidden attribute kept, ACL private), second run refused ✅, rollback ✅
(a session written after the move was kept), refusal while Claude runs ✅. Real dry run: 3,555 files, 1.10 GB,
18 transcripts, OK. Rehearsal leftovers you may delete: `D:\ClaudeStorage-rehearsal`, `D:\ClaudeStorage-rehearsal2`.

## Owner steps
1. Quit Claude Desktop (tray icon → Quit), close every terminal running `claude`, and VS Code/JetBrains.
2. Open **Windows PowerShell** (Start → "PowerShell"), then:
   ```
   cd "C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0\scripts\claude-storage"
   powershell -ExecutionPolicy Bypass -File .\migrate-claude-storage.ps1 -DryRun
   powershell -ExecutionPolicy Bypass -File .\migrate-claude-storage.ps1
   ```
   The last line must say `DONE`. If it says `STOPPED`, nothing was changed; read the reason.
3. Start Claude, open this project, resume the session and say "verify the Claude storage migration".
4. Undo at any time (Claude closed): `powershell -ExecutionPolicy Bypass -File .\migrate-claude-storage.ps1 -Rollback`.
5. Only after everything is confirmed, and only if you choose: delete `C:\Users\Sahil\.claude.pre-migration-<time>`
   (this is what actually frees the 1.1 GB on C:).

## Post-migration verification (for the resumed session)
- `(Get-Item ~\.claude -Force).LinkType` = `Junction`, target `D:\ClaudeStorage\.claude`; the log in `D:\ClaudeStorage` ends in DONE.
- Transcript count under `projects` = 18 (plus new ones); both Tamrivo sessions present with the same size; `/resume`
  lists Reel Studio and Tamrivo sessions.
- This session's new messages appear in `D:\ClaudeStorage\.claude\projects\C--Users-Sahil-OneDrive-Desktop-Reel-Studio-2-0\` (mtime updates).
- Settings, permissions, skills, plugins and MCP servers load; memories readable; signed in (no re-login); `gh auth status` OK.
- Reel Studio opens; `grep` of `~/.claude.json` and `settings.json` finds no path to a missing folder.

## Retention warning (recommend changing)
`cleanupPeriodDays` is not set, so Claude Code deletes transcripts **older than 30 days** at startup. The Tamrivo session
`315673bf-…` (last written 2026-10-15) would be removed around 2026-11-14. Recommended: add
`"cleanupPeriodDays": 3650` to `~/.claude/settings.json` (owner approval pending). Older sessions may already have been
cleaned up (several project folders hold 0–1 transcripts).
