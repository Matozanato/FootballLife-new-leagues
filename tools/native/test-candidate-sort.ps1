param(
    [Parameter(Mandatory)][string]$GameExecutable,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$Compiler = 'gcc'
)

$ErrorActionPreference = 'Stop'
$image = (Resolve-Path -LiteralPath $GameExecutable).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$test = Join-Path (Resolve-Path -LiteralPath $OutputDirectory).Path 'test-candidate-sort.exe'
& $Compiler -O2 -municode -Wall -Wextra -Werror (Join-Path $PSScriptRoot 'test_candidate_sort.c') -o $test
if ($LASTEXITCODE) { throw 'Candidate tests did not build.' }
& $test $image
if ($LASTEXITCODE) { throw "Candidate tests failed with exit code $LASTEXITCODE." }
