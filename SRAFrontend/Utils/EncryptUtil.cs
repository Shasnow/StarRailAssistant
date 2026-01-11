using System;
using System.Security.Cryptography;
using System.Text;

namespace SRAFrontend.Utils;

public static class EncryptUtil
{
    public static string EncryptString(string input)
    {
        var inputBytes = Encoding.UTF8.GetBytes(input);
        byte[] encryptedBytes;
        if (OperatingSystem.IsWindows())
        {
            encryptedBytes = ProtectedData.Protect(inputBytes, null, DataProtectionScope.CurrentUser);
        }
        else
        {
            encryptedBytes = inputBytes;
        }
        
        return Convert.ToBase64String(encryptedBytes);
    }

    public static string DecryptString(string input)
    {
        var encryptedBytes = Convert.FromBase64String(input);
        byte[] decryptedBytes;
        if (OperatingSystem.IsWindows())
        {
            decryptedBytes = ProtectedData.Unprotect(encryptedBytes, null, DataProtectionScope.CurrentUser);
        }
        else
        {
            decryptedBytes = encryptedBytes;
        }
        return Encoding.UTF8.GetString(decryptedBytes);
    }
}