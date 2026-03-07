Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bootstrapRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($bootstrapRoot)) {
    $bootstrapRoot = [System.AppDomain]::CurrentDomain.BaseDirectory
}
if ([string]::IsNullOrWhiteSpace($bootstrapRoot)) {
    throw "Unable to resolve setup root directory."
}
$installerPath = Join-Path $bootstrapRoot "Install-Hosted-Atelier.ps1"

if (-not (Test-Path -LiteralPath $installerPath)) {
    [System.Windows.Forms.MessageBox]::Show(
        "Install-Hosted-Atelier.ps1 was not found next to this wizard.",
        "Ko's Labyrnth Hosted Setup",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Ko's Labyrnth Hosted Setup Wizard"
$form.Size = New-Object System.Drawing.Size(760, 620)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "Install Ko's Labyrnth Hosted Atelier"
$lblTitle.Location = New-Object System.Drawing.Point(20, 20)
$lblTitle.Size = New-Object System.Drawing.Size(560, 28)
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 14)
$form.Controls.Add($lblTitle)

$lblSource = New-Object System.Windows.Forms.Label
$lblSource.Text = "Choose hosted suite source"
$lblSource.Location = New-Object System.Drawing.Point(20, 65)
$lblSource.Size = New-Object System.Drawing.Size(250, 22)
$form.Controls.Add($lblSource)

$radioDownload = New-Object System.Windows.Forms.RadioButton
$radioDownload.Text = "Download hosted suite zip"
$radioDownload.Location = New-Object System.Drawing.Point(35, 90)
$radioDownload.Size = New-Object System.Drawing.Size(220, 24)
$radioDownload.Checked = $true
$form.Controls.Add($radioDownload)

$radioLocal = New-Object System.Windows.Forms.RadioButton
$radioLocal.Text = "Use local hosted suite zip"
$radioLocal.Location = New-Object System.Drawing.Point(310, 90)
$radioLocal.Size = New-Object System.Drawing.Size(220, 24)
$form.Controls.Add($radioLocal)

$lblUrl = New-Object System.Windows.Forms.Label
$lblUrl.Text = "Hosted Suite Download URL"
$lblUrl.Location = New-Object System.Drawing.Point(20, 125)
$lblUrl.Size = New-Object System.Drawing.Size(180, 22)
$form.Controls.Add($lblUrl)

$txtUrl = New-Object System.Windows.Forms.TextBox
$txtUrl.Location = New-Object System.Drawing.Point(20, 148)
$txtUrl.Size = New-Object System.Drawing.Size(700, 28)
$txtUrl.Text = "https://github.com/<OWNER>/<REPO>/releases/download/<TAG>/atelier-hosted-suite-YYYYMMDD-HHMMSS.zip"
$form.Controls.Add($txtUrl)

$lblZip = New-Object System.Windows.Forms.Label
$lblZip.Text = "Local hosted suite zip"
$lblZip.Location = New-Object System.Drawing.Point(20, 185)
$lblZip.Size = New-Object System.Drawing.Size(160, 22)
$form.Controls.Add($lblZip)

$txtZip = New-Object System.Windows.Forms.TextBox
$txtZip.Location = New-Object System.Drawing.Point(20, 208)
$txtZip.Size = New-Object System.Drawing.Size(610, 28)
$form.Controls.Add($txtZip)

$btnBrowseZip = New-Object System.Windows.Forms.Button
$btnBrowseZip.Text = "Browse..."
$btnBrowseZip.Location = New-Object System.Drawing.Point(640, 207)
$btnBrowseZip.Size = New-Object System.Drawing.Size(80, 30)
$form.Controls.Add($btnBrowseZip)

$lblInstall = New-Object System.Windows.Forms.Label
$lblInstall.Text = "Install location"
$lblInstall.Location = New-Object System.Drawing.Point(20, 245)
$lblInstall.Size = New-Object System.Drawing.Size(120, 22)
$form.Controls.Add($lblInstall)

$txtInstall = New-Object System.Windows.Forms.TextBox
$txtInstall.Location = New-Object System.Drawing.Point(20, 268)
$txtInstall.Size = New-Object System.Drawing.Size(610, 28)
$txtInstall.Text = "$env:LOCALAPPDATA\KosLabyrnth\Atelier-Hosted"
$form.Controls.Add($txtInstall)

$btnBrowseInstall = New-Object System.Windows.Forms.Button
$btnBrowseInstall.Text = "Browse..."
$btnBrowseInstall.Location = New-Object System.Drawing.Point(640, 267)
$btnBrowseInstall.Size = New-Object System.Drawing.Size(80, 30)
$form.Controls.Add($btnBrowseInstall)

$lblApi = New-Object System.Windows.Forms.Label
$lblApi.Text = "Hosted API URL"
$lblApi.Location = New-Object System.Drawing.Point(20, 305)
$lblApi.Size = New-Object System.Drawing.Size(120, 22)
$form.Controls.Add($lblApi)

$txtApi = New-Object System.Windows.Forms.TextBox
$txtApi.Location = New-Object System.Drawing.Point(20, 328)
$txtApi.Size = New-Object System.Drawing.Size(700, 28)
$txtApi.Text = "http://127.0.0.1:9000"
$form.Controls.Add($txtApi)

$lblKernel = New-Object System.Windows.Forms.Label
$lblKernel.Text = "Hosted Kernel URL"
$lblKernel.Location = New-Object System.Drawing.Point(20, 365)
$lblKernel.Size = New-Object System.Drawing.Size(140, 22)
$form.Controls.Add($lblKernel)

$txtKernel = New-Object System.Windows.Forms.TextBox
$txtKernel.Location = New-Object System.Drawing.Point(20, 388)
$txtKernel.Size = New-Object System.Drawing.Size(700, 28)
$txtKernel.Text = "http://127.0.0.1:8000"
$form.Controls.Add($txtKernel)

$chkOverwrite = New-Object System.Windows.Forms.CheckBox
$chkOverwrite.Text = "Overwrite existing hosted install"
$chkOverwrite.Location = New-Object System.Drawing.Point(20, 425)
$chkOverwrite.Size = New-Object System.Drawing.Size(320, 24)
$chkOverwrite.Checked = $true
$form.Controls.Add($chkOverwrite)

$chkRunAfter = New-Object System.Windows.Forms.CheckBox
$chkRunAfter.Text = "Launch desktop after install"
$chkRunAfter.Location = New-Object System.Drawing.Point(360, 425)
$chkRunAfter.Size = New-Object System.Drawing.Size(220, 24)
$chkRunAfter.Checked = $true
$form.Controls.Add($chkRunAfter)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(20, 460)
$logBox.Size = New-Object System.Drawing.Size(700, 90)
$logBox.Multiline = $true
$logBox.ReadOnly = $true
$logBox.ScrollBars = "Vertical"
$form.Controls.Add($logBox)

$btnInstall = New-Object System.Windows.Forms.Button
$btnInstall.Text = "Install Hosted Suite"
$btnInstall.Location = New-Object System.Drawing.Point(520, 550)
$btnInstall.Size = New-Object System.Drawing.Size(200, 36)
$form.Controls.Add($btnInstall)

$folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
$openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog.Filter = "Zip Files (*.zip)|*.zip|All Files (*.*)|*.*"
$openFileDialog.Title = "Select Hosted Atelier Suite Zip"

function Set-SourceControls {
    $useDownload = $radioDownload.Checked
    $txtUrl.Enabled = $useDownload
    $txtZip.Enabled = -not $useDownload
    $btnBrowseZip.Enabled = -not $useDownload
}

function Append-Log {
    param([string]$Text)
    $logBox.AppendText($Text + [Environment]::NewLine)
}

$radioDownload.Add_CheckedChanged({ Set-SourceControls })
$radioLocal.Add_CheckedChanged({ Set-SourceControls })

$btnBrowseZip.Add_Click({
    if ($openFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtZip.Text = $openFileDialog.FileName
    }
})

$btnBrowseInstall.Add_Click({
    $folderDialog.SelectedPath = $txtInstall.Text
    if ($folderDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtInstall.Text = $folderDialog.SelectedPath
    }
})

$btnInstall.Add_Click({
    try {
        $logBox.Clear()
        Append-Log "Starting hosted install..."

        $installRoot = $txtInstall.Text.Trim()
        $apiBase = $txtApi.Text.Trim()
        $kernelBase = $txtKernel.Text.Trim()
        if ([string]::IsNullOrWhiteSpace($installRoot)) { throw "Install location is required." }
        if ([string]::IsNullOrWhiteSpace($apiBase)) { throw "Hosted API URL is required." }
        if ([string]::IsNullOrWhiteSpace($kernelBase)) { throw "Hosted Kernel URL is required." }

        $btnInstall.Enabled = $false
        $form.UseWaitCursor = $true
        [System.Windows.Forms.Application]::DoEvents()

        $powershellExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        $argList = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $installerPath,
            "-InstallRoot", $installRoot,
            "-ApiBaseUrl", $apiBase,
            "-KernelBaseUrl", $kernelBase
        )
        if ($radioDownload.Checked) {
            $downloadUrl = $txtUrl.Text.Trim()
            if ([string]::IsNullOrWhiteSpace($downloadUrl)) { throw "Hosted suite URL is required for download mode." }
            $argList += @("-DownloadUrl", $downloadUrl)
        } else {
            $zipPath = $txtZip.Text.Trim()
            if ([string]::IsNullOrWhiteSpace($zipPath)) { throw "Local hosted suite zip path is required." }
            if (-not (Test-Path -LiteralPath $zipPath)) { throw "Local hosted suite zip not found: $zipPath" }
            $argList += @("-SuiteZipPath", $zipPath)
        }
        if ($chkOverwrite.Checked) { $argList += "-Force" }
        if ($chkRunAfter.Checked) { $argList += "-RunAfterInstall" }

        $quotedArgs = $argList | ForEach-Object {
            if ($_ -match "\s") { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
        }
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $powershellExe
        $psi.Arguments = ($quotedArgs -join " ")
        $psi.WorkingDirectory = $bootstrapRoot
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        $null = $proc.Start()
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()

        if (-not [string]::IsNullOrWhiteSpace($stdout)) { Append-Log $stdout.Trim() }
        if (-not [string]::IsNullOrWhiteSpace($stderr)) { Append-Log ("ERROR: " + $stderr.Trim()) }
        if ($proc.ExitCode -ne 0) { throw "Installer process exited with code $($proc.ExitCode). See log for details." }

        Append-Log "Hosted install completed successfully."
        [System.Windows.Forms.MessageBox]::Show(
            "Hosted install completed successfully.",
            "Ko's Labyrnth Hosted Setup",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        Append-Log ("Install failed: " + $_.Exception.Message)
        [System.Windows.Forms.MessageBox]::Show(
            $_.Exception.Message,
            "Ko's Labyrnth Hosted Setup",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } finally {
        $form.UseWaitCursor = $false
        $btnInstall.Enabled = $true
    }
})

Set-SourceControls
[void]$form.ShowDialog()
