# -*- coding: utf-8 -*-
"""Android-specific I/O helpers.

These functions are pass-through no-ops on desktop and only activate the
pyjnius / MediaStore code path on Android. The Kivy UI calls them so that the
same app runs both locally (for testing) and on the device.
"""
import os

from kivy.utils import platform

IS_ANDROID = platform == "android"


def get_display_name(uri_or_path):
    """Return the original filename for a path or a content:// URI."""
    if not uri_or_path.startswith("content://"):
        return os.path.basename(uri_or_path)

    name = None
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        resolver = PythonActivity.mActivity.getContentResolver()
        Uri = autoclass("android.net.Uri")
        OpenableColumns = autoclass("android.provider.OpenableColumns")

        cursor = resolver.query(Uri.parse(uri_or_path), None, None, None, None)
        if cursor is not None:
            idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if idx >= 0 and cursor.moveToFirst():
                name = cursor.getString(idx)
            cursor.close()
    except Exception:
        name = None

    return name or "image.jpg"


def resolve_input(uri_or_path, dest):
    """Return a real file path readable by cv2.

    If the input is a content:// URI, copy its bytes to ``dest`` and return
    that path. Otherwise return the original path unchanged.
    """
    if not uri_or_path.startswith("content://"):
        return uri_or_path
    _copy_uri_to_file(uri_or_path, dest)
    return dest


def save_to_downloads(src_path, display_name):
    """Copy ``src_path`` into the public Downloads folder (Android 10+)."""
    if not IS_ANDROID:
        return False

    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        resolver = PythonActivity.mActivity.getContentResolver()
        ContentValues = autoclass("android.content.ContentValues")
        Environment = autoclass("android.os.Environment")
        Files = autoclass("java.nio.file.Files")
        Paths = autoclass("java.nio.file.Paths")
        Downloads = autoclass("android.provider.MediaStore$Downloads")

        values = ContentValues()
        values.put("_display_name", display_name)
        values.put("mime_type", "image/jpeg")
        values.put("relative_path", Environment.DIRECTORY_DOWNLOADS + "/")

        uri = resolver.insert(Downloads.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            return False

        out = resolver.openOutputStream(uri)
        if out is None:
            return False
        try:
            Files.copy(Paths.get(src_path), out)
        finally:
            out.close()
        return True
    except Exception:
        return False


def _copy_uri_to_file(uri, dest):
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    resolver = PythonActivity.mActivity.getContentResolver()
    Uri = autoclass("android.net.Uri")

    inp = resolver.openInputStream(Uri.parse(uri))
    FileOutputStream = autoclass("java.io.FileOutputStream")
    out = FileOutputStream(dest)

    Byte = autoclass("java.lang.Byte")
    Array = autoclass("java.lang.reflect.Array")
    buf = Array.newInstance(Byte.TYPE, 8192)

    try:
        while True:
            n = inp.read(buf)
            if n <= 0:
                break
            out.write(buf, 0, n)
    finally:
        out.close()
        inp.close()
