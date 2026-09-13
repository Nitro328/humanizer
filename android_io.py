# -*- coding: utf-8 -*-
"""Android-specific I/O helpers (pass-through no-ops on desktop)."""
import os

from kivy.utils import platform

IS_ANDROID = platform == "android"


def get_display_name(uri_str):
    """Return the original filename for a path or a content:// URI."""
    if not uri_str.startswith("content://"):
        return os.path.basename(uri_str)

    name = None
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        resolver = PythonActivity.mActivity.getContentResolver()
        Uri = autoclass("android.net.Uri")
        OpenableColumns = autoclass("android.provider.OpenableColumns")

        cursor = resolver.query(Uri.parse(uri_str), None, None, None, None)
        if cursor is not None:
            idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if idx >= 0 and cursor.moveToFirst():
                name = cursor.getString(idx)
            cursor.close()
    except Exception:
        name = None

    return name or "image.jpg"


def copy_uri_to_file(uri_str, dest):
    """Copy a content:// URI into a local file. Returns True on success."""
    if not IS_ANDROID:
        return False

    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        resolver = PythonActivity.mActivity.getContentResolver()
        Uri = autoclass("android.net.Uri")

        inp = resolver.openInputStream(Uri.parse(uri_str))
        if inp is None:
            return False

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
        return True
    except Exception:
        return False


def save_to_downloads(src_path, display_name):
    """Copy src_path into the public Downloads folder (Android 10+)."""
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
