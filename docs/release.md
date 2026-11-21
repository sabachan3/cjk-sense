# Publishing a release

Publishing is the owner's step. Everything before it is prepared and checked by
`scripts/e2e.sh` and CI; this page is the list of things only the owner can do.
`VERSION` below is the version in `pyproject.toml` (first release: `0.1.0`).

## Once: connect PyPI to this repository (trusted publishing)

No token is created or stored. PyPI is told which workflow of which repository may publish.

1. Sign in at https://pypi.org (the account needs two-factor authentication).
2. Open https://pypi.org/manage/account/publishing/ and, under "Add a new pending publisher",
   choose GitHub and fill in exactly:

   | field | value |
   |---|---|
   | PyPI Project Name | `cjk-sense` |
   | Owner | `sabachan3` |
   | Repository name | `cjk-sense` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

   A pending publisher does not reserve the name. The name was free on 2026-11-22
   (`curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/cjk-sense/json` printed 404);
   check again on the day.
3. Optional, on GitHub: Settings, Environments, New environment `pypi`, and add yourself as a
   required reviewer. The publish job then waits for one click after the checks have passed.
   Without this step GitHub creates the environment by itself on the first run and nothing waits.

## Each release

1. Decide the version. For a version after the first, change it in `pyproject.toml` and in
   `cjk_sense/__init__.py` (a gate test keeps them equal) and add a `CHANGELOG.md` entry.
2. Write the date into the changelog heading: `## VERSION (not released yet)` becomes
   `## VERSION (YYYY-MM-DD)`.
3. Check, commit, push, and wait for CI to end green on that commit:

   ```bash
   uv run --no-project python evals/release_ready.py vVERSION   # tag, package and changelog agree
   scripts/test.sh
   scripts/e2e.sh        # builds sdist and wheel, checks their contents, installs and runs both
   git commit -am "Release VERSION" && git push
   gh run watch          # the ci run of that push
   ```

4. Tag that commit and publish a GitHub release. Publishing the release starts
   `.github/workflows/release.yml`:

   ```bash
   git tag -a vVERSION -m "cjk-sense VERSION" && git push origin vVERSION
   gh release create vVERSION --title "cjk-sense VERSION" --notes "See CHANGELOG.md: https://github.com/sabachan3/cjk-sense/blob/main/CHANGELOG.md"
   gh run watch          # the release run; approve the pypi environment if you set a reviewer
   ```

   The workflow runs all of CI again, refuses a tag that is not `v` + the version in
   `pyproject.toml` or a changelog entry without a date, builds the two files, checks their
   contents, installs and runs both, and only then uploads exactly those two files.
   Starting it by hand instead (Actions, release, Run workflow, type the version) does the same
   without a GitHub release.
5. Verify from a directory outside the repository. `--refresh` makes uv ask PyPI again:

   ```bash
   uvx --refresh cjk-sense --help
   uvx cjk-sense --version                      # prints: cjk-sense VERSION
   uvx --from playwright playwright install chromium-headless-shell
   uvx cjk-sense check https://example.com      # any page; a report with a verdict means it runs
   ```

   Look at https://pypi.org/project/cjk-sense/ once: the README renders, its links open, the
   licence says MIT, the author is the account name and no email address is shown.
6. After the first release only, in one commit:
   - `README.md`, section Install: put the PyPI commands first, remove the sentence that says
     they do not work yet, keep the install-from-GitHub command below them.
   - `docs/github-actions.yml`: replace both `uvx --from git+https://github.com/sabachan3/cjk-sense cjk-sense`
     with `uvx cjk-sense`.
   - `PROGRESS.md`: "Not on PyPI" becomes the published version; remove the next step about publishing.

## A bad release

A version number can never be uploaded twice, not even after deleting it. So:

1. Yank it: https://pypi.org/manage/project/cjk-sense/releases/, the version, Options, Yank, and
   give a reason. A yanked version stays downloadable for someone who pins it exactly
   (`cjk-sense==VERSION`) and is skipped by every other install. Yanking can be undone on the
   same page. Do not delete: deleting breaks pinned installs and frees nothing.
2. Fix, raise the version (`0.1.0` to `0.1.1`), add the changelog entry, and release again with
   the steps above.
3. Mark the GitHub release as a pre-release or edit its notes to point at the fixed version:
   `gh release edit vVERSION --prerelease --notes "Yanked, use ..."`.

If the release workflow fails before the publish job, nothing reached PyPI: fix, move nothing,
and start it again by hand (Actions, release, Run workflow) or delete and recreate the GitHub
release. If it fails inside the publish job, look at PyPI first to see whether the files are there.

## Licences (checked 2026-11-22 for 0.1.0)

cjk-sense is MIT (`LICENSE`, `license = "MIT"` in `pyproject.toml`).

The wheel and the sdist hold only this repository's own source, its README, changelog and
licence. No font file, no browser, no third-party code and no data set is inside.

| what a user gets at install | version resolved on 2026-11-22 | licence | how it arrives |
|---|---|---|---|
| playwright | 1.65.2 | Apache-2.0 | dependency, installed by pip or uv |
| greenlet (needed by playwright) | 3.5.6 | MIT AND PSF-2.0 | dependency of playwright |
| Node.js and the Playwright driver | inside the playwright wheel | MIT and the notices in `playwright/driver/package/ThirdPartyNotices.txt` | part of playwright's own distribution |
| Chromium | fetched by `playwright install`, or the user's own Chrome or Edge | BSD-3-Clause and others; Chrome and Edge under their vendors' terms | downloaded by the user, never redistributed by cjk-sense |

Older playwright versions that `playwright>=1.49` still allows also install pyee (MIT) and
typing-extensions (PSF-2.0).

The font tables (`services/fonts/fonts_lib.py`) are this repository's own source, present since
its first commit: family names of fonts that ship with macOS, Windows, iOS and Android, and
substrings of the names of common web fonts, each with the region it draws Han characters for.
The entries the browser eval exercises were confirmed in Chromium on macOS and Edge on
Windows 11; iOS and Android entries are unverified predictions (`docs/results.md`). The table
is a list of names and statements about them and holds no font data. The repository records no
outside source for it (no file was imported from another project). Font names are trademarks
of their owners and are used only to name the fonts.

The script ranges in `services/detect/detect_lib.py` are Unicode block boundaries written as
ten short ranges; no Unicode data file is bundled (Python's own `unicodedata` is used).

Conflicts: none found. Apache-2.0, MIT, PSF-2.0 and BSD-3-Clause are all compatible with
distributing an MIT tool that depends on them without copying their code. Not checked: the
licences of every package inside Playwright's bundled driver beyond its notices file.
