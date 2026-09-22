// Common Item Dialog: the same Windows Explorer UI for files and folders.
// Kept compatible with the compiler included in Windows PowerShell 5.1.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

public static class NativePicker
{
    private const int Cancelled = unchecked((int)0x800704C7);

    public static string Show(string root, string kind)
    {
        root = Path.GetFullPath(root);
        if (!Directory.Exists(root)) throw new DirectoryNotFoundException(root);
        if (kind != "folder" && kind != "file") throw new ArgumentException("Invalid picker kind");

        var dialog = (IFileDialog)new FileOpenDialog();
        IShellItem initial = null;
        IShellItem selected = null;
        using (var owner = new Form())
        using (var timer = new Timer())
        {
            try
            {
                // SetFolder overrides Windows' remembered location on EVERY opening.
                var shellItemId = typeof(IShellItem).GUID;
                Marshal.ThrowExceptionForHR(SHCreateItemFromParsingName(root, IntPtr.Zero, ref shellItemId, out initial));
                dialog.SetFolder(initial);
                uint options;
                dialog.GetOptions(out options);
                // Filesystem only, existing paths, no working-directory changes/recent entries.
                options |= 0x40 | 0x800 | 0x8 | 0x02000000;
                options |= kind == "folder" ? 0x20u : 0x1000u;
                dialog.SetOptions(options);
                dialog.SetTitle(kind == "folder" ? "Seleccionar carpeta de la pieza" : "Seleccionar archivo vinculado");

                // The launcher's SW_HIDE must not leave the native dialog invisible.
                owner.Text = "INTEPLAST";
                owner.ShowInTaskbar = false;
                owner.Opacity = 0;
                owner.TopMost = true;
                owner.StartPosition = FormStartPosition.CenterScreen;
                owner.Size = new System.Drawing.Size(1, 1);
                timer.Interval = 100;
                timer.Tick += delegate
                {
                    var popup = FindDialog(owner.Handle);
                    if (popup == IntPtr.Zero) return;
                    ShowWindow(popup, 5);
                    if (!IsWindowVisible(popup)) return;
                    SetForegroundWindow(popup);
                    Console.Error.WriteLine("INTEPLAST_PICKER_READY");
                    timer.Stop();
                };
                owner.Show();
                owner.Activate();
                timer.Start();
                int result = dialog.Show(owner.Handle);
                if (result == Cancelled) return null;
                Marshal.ThrowExceptionForHR(result);
                dialog.GetResult(out selected);
                return FileSystemPath(selected);
            }
            finally
            {
                timer.Stop();
                if (selected != null) Marshal.ReleaseComObject(selected);
                if (initial != null) Marshal.ReleaseComObject(initial);
                Marshal.ReleaseComObject(dialog);
            }
        }
    }

    private static string FileSystemPath(IShellItem item)
    {
        IntPtr value;
        item.GetDisplayName(0x80058000, out value); // SIGDN_FILESYSPATH
        try { return Marshal.PtrToStringUni(value); }
        finally { Marshal.FreeCoTaskMem(value); }
    }

    private delegate bool EnumWindowsCallback(IntPtr window, IntPtr parameter);
    private static IntPtr FindDialog(IntPtr owner)
    {
        IntPtr dialog = IntPtr.Zero;
        EnumThreadWindows(GetCurrentThreadId(), delegate(IntPtr window, IntPtr parameter)
        {
            if (GetWindow(window, 4) != owner) return true;
            var name = new StringBuilder(256);
            GetClassName(window, name, name.Capacity);
            if (name.ToString() != "#32770") return true;
            dialog = window;
            return false;
        }, IntPtr.Zero);
        return dialog;
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = true)]
    private static extern int SHCreateItemFromParsingName(string path, IntPtr context, ref Guid id, out IShellItem item);
    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] private static extern bool EnumThreadWindows(uint thread, EnumWindowsCallback callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern IntPtr GetWindow(IntPtr window, uint command);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr window, StringBuilder name, int count);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window, int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);

    [ComImport, Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    private class FileOpenDialog { }

    // COM vtable order through GetResult; unused methods still occupy their slots.
    [ComImport, Guid("42F85136-DB7E-439C-85F1-E4075D135FC8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IFileDialog
    {
        [PreserveSig] int Show(IntPtr owner);
        void SetFileTypes(uint count, IntPtr filters);
        void SetFileTypeIndex(uint index);
        void GetFileTypeIndex(out uint index);
        void Advise(IntPtr events, out uint cookie);
        void Unadvise(uint cookie);
        void SetOptions(uint options);
        void GetOptions(out uint options);
        void SetDefaultFolder(IShellItem folder);
        void SetFolder(IShellItem folder);
        void GetFolder(out IShellItem folder);
        void GetCurrentSelection(out IShellItem item);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string name);
        void GetFileName(out IntPtr name);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string title);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void GetResult(out IShellItem item);
    }

    [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellItem
    {
        void BindToHandler(IntPtr context, ref Guid handler, ref Guid id, out IntPtr result);
        void GetParent(out IShellItem parent);
        void GetDisplayName(uint format, out IntPtr name);
        void GetAttributes(uint mask, out uint attributes);
        void Compare(IShellItem item, uint hint, out int order);
    }
}
