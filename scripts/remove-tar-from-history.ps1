# Remove open-notebook-image.tar from branch history so push succeeds (file > 100MB).
# Run from repo root.
#
# Option A - Git Bash (recommended; included with Git for Windows):
#   bash scripts/remove-tar-from-history.sh
#   git push --force-with-lease origin <branch>
#
# Option B - WSL:
#   wsl bash scripts/remove-tar-from-history.sh
#   git push --force-with-lease origin <branch>
#
# Requires: pip install git-filter-repo (then run the .sh script).

$branch = if ($args[0]) { $args[0] } else { git branch --show-current }
Write-Host ""
Write-Host "The large file is in this branch's history. To remove it:" -ForegroundColor Yellow
Write-Host "  1. Install git-filter-repo:  pip install git-filter-repo" -ForegroundColor Cyan
Write-Host "  2. In Git Bash (or WSL), from repo root run:" -ForegroundColor Cyan
Write-Host "     bash scripts/remove-tar-from-history.sh" -ForegroundColor White
Write-Host "  3. Force-push:" -ForegroundColor Cyan
Write-Host "     git push --force-with-lease origin $branch" -ForegroundColor White
Write-Host ""
$run = Read-Host "Run the script now via Git Bash? (y/n)"
if ($run -eq 'y' -or $run -eq 'Y') {
    $bash = $env:ProgramFiles + "\Git\bin\bash.exe"
    if (Test-Path $bash) {
        & $bash -c "cd '$PWD'; bash scripts/remove-tar-from-history.sh '$branch'"
    } else {
        Write-Host "Git Bash not found at $bash" -ForegroundColor Red
    }
}
