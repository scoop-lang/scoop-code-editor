param([int]$EditorPid, [string]$Directory)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$initial = ([string][char]0x9996) + [string]([char]13) + [char]10 + 'A' + [char]::ConvertFromUtf32(0x1f642) + 'B' + [char]13 + [char]10 + [char]0x5c3e
$committed = $initial.Replace('B', ([string][char]0x4e2d + 'B'))
$selection = 'A' + [char]::ConvertFromUtf32(0x1f642)
function Wait-For($Description, [scriptblock]$Check) {
    $end = [DateTime]::UtcNow.AddSeconds(18)
    while ([DateTime]::UtcNow -lt $end) {
        $value = & $Check
        if ($value) { return $value }
        if (-not (Get-Process -Id $EditorPid -ErrorAction SilentlyContinue)) {
            throw "Editor exited before $Description"
        }
        Start-Sleep -Milliseconds 60
    }
    throw "Timed out waiting for $Description"
}
function Wait-Marker($Name) {
    $null = Wait-For $Name { Test-Path (Join-Path $Directory $Name) }
}

Wait-Marker 'ready'
$client = Wait-For 'UI Automation document' {
    $hwnd = (Get-Process -Id $EditorPid).MainWindowHandle
    if ($hwnd -eq 0) { return }
    $window = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
    $tree = [System.Windows.Automation.TreeScope]::Subtree
    $condition = [System.Windows.Automation.Condition]::TrueCondition
    foreach ($element in $window.FindAll($tree, $condition)) {
        $range = $null
        if ($element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$range) -and
            $range.DocumentRange.GetText(-1) -ceq $initial) {
            return $element
        }
    }
}
$text = $client.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
New-Item -ItemType File -Path (Join-Path $Directory start) | Out-Null
Wait-Marker 'preedit'
Wait-Marker 'committed'
$null = Wait-For 'committed UI Automation text' { $text.DocumentRange.GetText(-1) -ceq $committed }
$selected = $text.DocumentRange.FindText($selection, $false, $false)
if (-not $selected) { throw 'UI Automation could not find the non-ASCII selection' }
$selected.Select()
Wait-Marker 'selection'
$value = $client.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
$value.SetValue('accessible replacement')
