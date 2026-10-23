# Repository migration — Reel Studio → Reel Studio 2.0 (2026-10-23)

## What moved
| | Source (read-only reference) | Destination (all new work) |
|---|---|---|
| Repository | https://github.com/sahilkarande0918-cmd/Open_PS04_ (the original repo, renamed; GitHub id `R_kgDOVMIGEQ`) | https://github.com/sahilkarande0918-cmd/Reel-Studio (new repo, `R_kgDOVU896w`, empty before migration) |
| Local folder | `C:\dev\Reel-Studio` (kept unchanged; its `origin` now points to `Open_PS04_`) | `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0` (`origin` = new repo, `source` = `Open_PS04_` fetch-only, push disabled) |

## Method
1. Checked: GitHub auth (`sahilkarande0918-cmd`, scopes repo/workflow), destination had zero refs, source refs were
   `main` `a28eacac1a8c60b4c8ddcfdf6be8c2b4dfaec8da` and `feature/topic-studio` `7419b774…`; no tags, no Git LFS, no
   submodules; local worktree clean; the local-only branch `feature/ui-audit` (`d174ff1`) is already contained in `main`.
2. Secret scan of every commit (Supabase secret keys, JWTs, GitHub/OpenAI/AWS/Meta tokens, private keys, assigned
   secrets): no findings. The only env file ever tracked is `.env.example`, with placeholders only.
3. One operation: `git clone --bare` of the source, then `git push <dest> 'refs/heads/*' 'refs/tags/*'`
   (GitHub's internal `refs/pull/*` excluded).

## Verification (fresh bare clones of both repos)
| Check | Source | Destination |
|---|---|---|
| `main` commit | `a28eacac1a8c60b4c8ddcfdf6be8c2b4dfaec8da` | same |
| `main` tree | `02ae2cf5c8ad223ebb555250a65f2836138e29e7` | same |
| Tracked files | 295 | 295, identical paths and blob ids (`git ls-tree -r` diff empty) |
| Commits (all refs) | 87 | 87, identical author/committer/date hash |
| `feature/topic-studio` | `7419b774…` tree `d830fe9f…` | same |
| Tags / LFS / submodules | none | none |
| `git fsck` | clean | clean |

## Owner-requested change after verification
The owner asked that only their own commits remain. Two one-line placeholder commits by other people were removed from
the destination's history (not re-attributed): `c24e41a` "Add new document for Reel Studio" (`docs/sahil`) and
`a6650c9` "Add new file documentation file" (`docs/sk`). Done with `git filter-branch --index-filter 'git rm --cached
docs/sk docs/sahil' --prune-empty` on `main`, then one `--force-with-lease` push to the destination only.
- New `main`: `6e94ddf4be46282feaa95a7cd953610ea2eedb2d`, tree `ac05e9f082c681cc66c74fe214160bbd427050e1`.
- 85 commits, every one authored by the owner; dates and messages unchanged.
- Tree differs from the source `main` only by those two deleted placeholder files (293 tracked files).
- `feature/topic-studio` predates them and is unchanged. `Open_PS04_` was not modified.

## Not in Git (configure locally)
`.env` / `.env.local` files, `node_modules`, the Python venv (`%LOCALAPPDATA%\reel-studio\venv`), model weights, recordings
and renders (`%LOCALAPPDATA%\reel-studio\data`), Ollama models, Supabase CLI link state.

## Deployment linkage
The production engine and the Vercel project still run from the original repo/folder until they are deliberately
re-pointed; pushing to the new repository does not by itself deploy to production.
