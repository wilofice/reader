"""Terminal focus events, plus a lightweight native macOS foreground check."""

from collections import deque
import ctypes
import os
import sys
import time

FOCUS_EVENT = -2


class MacForeground:
    def __init__(self):
        ctypes.CDLL('/System/Library/Frameworks/AppKit.framework/AppKit')
        self.objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
        self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_getClass.restype = ctypes.c_void_p
        self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
        self.objc.sel_registerName.restype = ctypes.c_void_p
        self.address = ctypes.cast(self.objc.objc_msgSend, ctypes.c_void_p).value
        self.pool_class = self.objc.objc_getClass(b'NSAutoreleasePool')
        self.workspace_class = self.objc.objc_getClass(b'NSWorkspace')
        self.calls = {}

    def call(self, receiver, method, result=ctypes.c_void_p):
        if not receiver:
            return None
        key = method, result
        if key not in self.calls:
            function = ctypes.CFUNCTYPE(result, ctypes.c_void_p, ctypes.c_void_p)(self.address)
            self.calls[key] = function, self.objc.sel_registerName(method.encode())
        function, selector = self.calls[key]
        return function(receiver, selector)

    def bundle(self):
        pool = self.call(self.call(self.pool_class, 'alloc'), 'init')
        try:
            workspace = self.call(self.workspace_class, 'sharedWorkspace')
            app = self.call(workspace, 'frontmostApplication')
            name = self.call(app, 'bundleIdentifier')
            value = self.call(name, 'UTF8String', ctypes.c_char_p)
            return value.decode('utf-8') if value else None
        finally:
            self.call(pool, 'drain', None)


class TerminalFocus:
    def __init__(self, environment=None, now=None):
        env = os.environ if environment is None else environment
        self.now = now or time.monotonic
        self.reported = True
        self.received_reports = False
        self.native = None
        self.native_active = True
        self.checked = float('-inf')
        programs = {'iTerm.app': 'com.googlecode.iterm2', 'Apple_Terminal': 'com.apple.Terminal'}
        self.bundle_id = programs.get(env.get('TERM_PROGRAM'))
        if sys.platform == 'darwin' and self.bundle_id and not env.get('SSH_CONNECTION') and not env.get('SSH_TTY'):
            try:
                self.native = MacForeground()
            except (OSError, AttributeError):
                pass

    def event(self, focused):
        self.received_reports = True
        self.reported = focused
        self.checked = float('-inf')

    def focused(self):
        # The terminal knows its own window/tab. Application identity can lag
        # or be inherited from another terminal (for example in a multiplexer).
        if self.received_reports:
            return self.reported
        if not self.reported:
            return False
        now = self.now()
        if self.native is not None and now - self.checked >= 1:
            try:
                bundle = self.native.bundle()
                if bundle is not None:
                    self.native_active = bundle == self.bundle_id
            except (OSError, ValueError):
                pass
            self.checked = now
        return self.reported and self.native_active


class FocusScreen:
    """Consume CSI I/O without confusing focus-out with the quit Escape key."""
    def __init__(self, screen, focus):
        self.screen, self.focus = screen, focus
        self.wait_ms = 1000
        self.buffer = deque()

    def __getattr__(self, name):
        return getattr(self.screen, name)

    def timeout(self, milliseconds):
        self.wait_ms = milliseconds
        self.screen.timeout(milliseconds)

    def focused(self):
        return self.focus.focused()

    def getch(self):
        key = self.buffer.popleft() if self.buffer else self.screen.getch()
        if key != -1:
            self.focus.checked = float('-inf')
        if key != 27:
            return key
        consumed = []
        self.screen.timeout(30)
        try:
            following = self.screen.getch()
            if following != -1:
                consumed.append(following)
            if following == ord('['):
                final = self.screen.getch()
                if final != -1:
                    consumed.append(final)
                if final in (ord('I'), ord('O')):
                    self.focus.event(final == ord('I'))
                    return FOCUS_EVENT
            self.buffer.extendleft(reversed(consumed))
            return 27
        finally:
            self.screen.timeout(self.wait_ms)


def is_focused(screen):
    # Fake test screens and simple alternate viewers need no platform dependency.
    method = getattr(screen, 'focused', None)
    return bool(method()) if callable(method) else True


def enable_reports():
    if sys.stdout.isatty() and os.environ.get('TERM') != 'dumb':
        sys.stdout.write('\x1b[?1004h')
        sys.stdout.flush()
        return True
    return False


def disable_reports():
    sys.stdout.write('\x1b[?1004l')
    sys.stdout.flush()
