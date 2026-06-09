using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;

namespace KakaoEmoticonSetupV92
{
    internal static class Program
    {
        private const string PayloadResourceName = "payload.zip";
        private const string InstallBatchName = "00_STEP_2_PORTABLE_INSTALL_NOW.bat";

        private static int Main()
        {
            Console.Title = "Kakao Emoticon Direct Creation Helper v92 Setup";
            Console.WriteLine();
            Console.WriteLine("============================================================");
            Console.WriteLine(" Kakao Emoticon Direct Creation Helper v92 - Setup");
            Console.WriteLine("============================================================");
            Console.WriteLine();

            string workDir = Path.Combine(
                Path.GetTempPath(),
                "KakaoEmoticonV92_Setup_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8)
            );

            try
            {
                Directory.CreateDirectory(workDir);
                string payloadPath = Path.Combine(workDir, "payload.zip");

                Console.WriteLine("[v92] Extracting embedded installer payload...");
                using (Stream input = Assembly.GetExecutingAssembly().GetManifestResourceStream(PayloadResourceName))
                {
                    if (input == null)
                    {
                        throw new InvalidOperationException("Embedded payload was not found.");
                    }

                    using (FileStream output = File.Create(payloadPath))
                    {
                        input.CopyTo(output);
                    }
                }

                Console.WriteLine("[v92] Expanding package files...");
                ZipFile.ExtractToDirectory(payloadPath, workDir);

                string installBatch = Path.Combine(workDir, InstallBatchName);
                if (!File.Exists(installBatch))
                {
                    throw new FileNotFoundException("Portable installer BAT was not found after extraction.", installBatch);
                }

                Console.WriteLine("[v92] Starting portable install flow...");
                ProcessStartInfo startInfo = new ProcessStartInfo();
                startInfo.FileName = "cmd.exe";
                startInfo.Arguments = "/C \"\"" + installBatch + "\"\"";
                startInfo.WorkingDirectory = workDir;
                startInfo.UseShellExecute = false;

                using (Process process = Process.Start(startInfo))
                {
                    process.WaitForExit();
                    Console.WriteLine();
                    Console.WriteLine(process.ExitCode == 0
                        ? "[v92] Setup finished."
                        : "[WARN] Setup finished with error code " + process.ExitCode + ".");
                    Console.WriteLine("[v92] Temporary extracted files: " + workDir);
                    Console.WriteLine();
                    Console.WriteLine("Press Enter to close this window.");
                    Console.ReadLine();
                    return process.ExitCode;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("[ERROR] Setup could not continue.");
                Console.WriteLine(ex.Message);
                Console.WriteLine("[v92] Temporary setup folder: " + workDir);
                Console.WriteLine();
                Console.WriteLine("Press Enter to close this window.");
                Console.ReadLine();
                return 1;
            }
        }
    }
}
