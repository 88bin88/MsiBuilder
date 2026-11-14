using System;
using System.IO;
using System.Diagnostics;
using System.Reflection;

class MsiSelfExtractor
{
    // 尾部索引格式：magic(8) + offset(8, int64 LE) + size(8, int64 LE) = 24 字节
    const int TAIL_LEN = 24;
    static readonly byte[] MAGIC = new byte[] { 0x4D, 0x53, 0x49, 0x32, 0x45, 0x58, 0x45, 0x21 }; // "MSI2EXE!"

    [STAThread]
    static int Main(string[] args)
    {
        string tmpDir = null;
        try
        {
            string self = null;
            try { self = Assembly.GetExecutingAssembly().Location; } catch { }
            if (string.IsNullOrEmpty(self))
                self = Process.GetCurrentProcess().MainModule.FileName;

            long offset, size;
            if (!ReadTail(self, out offset, out size))
                return 2;

            tmpDir = Path.Combine(Path.GetTempPath(), "MsiSetup_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tmpDir);
            string msiPath = Path.Combine(tmpDir, "setup.msi");

            Extract(self, offset, size, msiPath);

            string msiexec = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "msiexec.exe");
            var psi = new ProcessStartInfo();
            psi.FileName = msiexec;
            // 与双击 MSI 完全相同的调用方式：完整安装向导 UI
            psi.Arguments = "/i \"" + msiPath + "\"";
            psi.UseShellExecute = false;

            Process p = Process.Start(psi);
            p.WaitForExit();

            try { Directory.Delete(tmpDir, true); } catch { }
            return p.ExitCode;
        }
        catch (Exception ex)
        {
            try
            {
                File.AppendAllText(Path.Combine(Path.GetTempPath(), "MsiSelfExtract_error.log"),
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + ex.ToString() + Environment.NewLine);
            }
            catch { }
            try
            {
                System.Windows.Forms.MessageBox.Show(
                    "安装程序启动失败：" + Environment.NewLine + ex.Message,
                    "错误", System.Windows.Forms.MessageBoxButtons.OK,
                    System.Windows.Forms.MessageBoxIcon.Error);
            }
            catch { }
            return 1;
        }
    }

    static bool ReadTail(string path, out long offset, out long size)
    {
        offset = 0; size = 0;
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            long len = fs.Length;
            if (len < TAIL_LEN) return false;
            fs.Seek(len - TAIL_LEN, SeekOrigin.Begin);
            byte[] tail = new byte[TAIL_LEN];
            int read = 0;
            while (read < TAIL_LEN)
            {
                int n = fs.Read(tail, read, TAIL_LEN - read);
                if (n <= 0) return false;
                read += n;
            }
            for (int i = 0; i < MAGIC.Length; i++)
                if (tail[i] != MAGIC[i]) return false;
            offset = BitConverter.ToInt64(tail, 8);
            size = BitConverter.ToInt64(tail, 16);
            if (offset <= 0 || size <= 0 || offset + size > len - TAIL_LEN) return false;
            return true;
        }
    }

    static void Extract(string self, long offset, long size, string dest)
    {
        using (var src = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (var dst = new FileStream(dest, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            src.Seek(offset, SeekOrigin.Begin);
            byte[] buf = new byte[81920];
            long left = size;
            while (left > 0)
            {
                int n = src.Read(buf, 0, (int)Math.Min((long)buf.Length, left));
                if (n <= 0) break;
                dst.Write(buf, 0, n);
                left -= n;
            }
        }
    }
}
