"""Windows launcher ownership and window activation, scoped to the save directory."""

import ctypes
import hashlib
import os
import time
from ctypes import wintypes


class ProfileInstance:
    def __init__(self, directory):
        identity = os.path.normcase(str(directory.resolve())).encode("utf-8")
        self.name = "WinstonES-" + hashlib.sha256(identity).hexdigest()
        self.handle = None

    def acquire(self):
        if os.name != "nt":
            return True
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        handle = kernel.CreateMutexW(None, False, "Global\\" + self.name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        result = kernel.WaitForSingleObject(handle, 0)
        if result in (0, 0x80):  # Acquired, including recovery if the owner crashed.
            self.handle = handle
            return True
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        if result != 0x102:  # WAIT_TIMEOUT means another launcher owns the profile.
            raise ctypes.WinError(error)
        return False

    def close(self):
        if self.handle:
            self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def tag_window(self, hwnd):
        if os.name == "nt" and hwnd:
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
            user.SetPropW(hwnd, self.name, 1)

    def show_existing(self):
        """Allow a just-started owner a moment to create and tag its window."""
        if os.name != "nt":
            return
        user = ctypes.WinDLL("user32", use_last_error=True)
        visitor = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user.EnumWindows.argtypes = [visitor, wintypes.LPARAM]
        user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        user.GetPropW.restype = wintypes.HANDLE
        user.IsIconic.argtypes = user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        user.FlashWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
        found = []

        @visitor
        def match(hwnd, _):
            if user.GetPropW(hwnd, self.name):
                found.append(hwnd)
                return False
            return True

        for _ in range(20):
            user.EnumWindows(match, 0)
            if found:
                hwnd = found[0]
                if user.IsIconic(hwnd):
                    user.ShowWindowAsync(hwnd, 9)  # SW_RESTORE
                if not user.SetForegroundWindow(hwnd):
                    user.FlashWindow(hwnd, True)
                return
            time.sleep(0.05)
