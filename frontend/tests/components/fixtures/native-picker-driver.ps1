# Opt-in integration test driver for our picker process only. Never selects a file.
param([int]$PickerProcessId, [string]$ExpectedRoot, [ValidateSet('close', 'cancel')][string]$Action = 'close')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Diagnostics;
public static class PickerTestWindow {
    private delegate bool Callback(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumThreadWindows(uint thread, Callback callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr window, StringBuilder name, int count);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr window, uint message, IntPtr wparam, IntPtr lparam);
    public static IntPtr Find(uint process) {
        IntPtr found = IntPtr.Zero;
        Process target;
        try { target = Process.GetProcessById((int)process); }
        catch (ArgumentException) { return found; }
        Callback inspect = delegate(IntPtr window, IntPtr parameter) {
            uint owner;
            GetWindowThreadProcessId(window, out owner);
            var name = new StringBuilder(256);
            GetClassName(window, name, name.Capacity);
            if (owner != process || !IsWindowVisible(window)) return true;
            if (name.ToString() != "#32770") return true;
            found = window;
            return false;
        };
        foreach (ProcessThread thread in target.Threads) {
            EnumThreadWindows((uint)thread.Id, inspect, IntPtr.Zero);
            if (found != IntPtr.Zero) break;
        }
        return found;
    }
}
'@
$dialogWindow = [PickerTestWindow]::Find($PickerProcessId)
if ($dialogWindow -eq [IntPtr]::Zero) { throw 'Picker dialog is not visible' }
try {
    $dialog = [Windows.Automation.AutomationElement]::FromHandle($dialogWindow)
    $controls = $dialog.FindAll([Windows.Automation.TreeScope]::Descendants, [Windows.Automation.Condition]::TrueCondition)
    $names = @($controls | ForEach-Object { $_.Current.Name })
    if (-not ($names | Where-Object { $_.Contains($ExpectedRoot) })) {
        throw ('Wrong initial folder. Address bars: ' + ($names -join ' | '))
    }
    if ($Action -eq 'cancel') {
        # WM_COMMAND / IDCANCEL is the native Cancel/Escape action.
        [void][PickerTestWindow]::PostMessage($dialogWindow, 0x0111, [IntPtr]2, [IntPtr]::Zero)
    } else {
        # WM_CLOSE is the dialog's title-bar X action.
        [void][PickerTestWindow]::PostMessage($dialogWindow, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
    }
    Write-Output 'Explorer address verified; native dialog closed.'
} finally {
    if ([PickerTestWindow]::Find($PickerProcessId) -ne [IntPtr]::Zero) {
        [void][PickerTestWindow]::PostMessage($dialogWindow, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
    }
}
