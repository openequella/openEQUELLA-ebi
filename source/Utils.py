import os
import platform
import csv


def getPlatform():
    ebiPlatform = "Python " + platform.python_version()
    system = platform.system()
    if system == "Windows":
        ebiPlatform += ", Windows " + platform.release()
    elif system == "Darwin":
        ebiPlatform += ", Mac OS " + platform.mac_ver()[0]
    elif system == "Linux":
        # Use freedesktop_os_release() for Python 3.10+ or fallback for older versions
        try:
            if hasattr(platform, "freedesktop_os_release"):
                os_info = platform.freedesktop_os_release()
                ebiPlatform += (
                    ", "
                    + os_info.get("NAME", "Linux")
                    + " "
                    + os_info.get("VERSION", "").strip()
                )
            else:
                ebiPlatform += ", Linux " + platform.release()
        except:
            ebiPlatform += ", Linux " + platform.release()
    else:
        ebiPlatform += ", " + platform.system()
    return ebiPlatform


def openFileForReading(filepath):
    """Safely open a file for binary reading with proper error handling.

    Args:
        filepath: Full path to the file to open

    Returns:
        File object opened in binary read mode

    Raises:
        Exception: If file doesn't exist or cannot be opened
    """
    try:
        # Final validation before opening
        if not os.path.exists(filepath):
            raise FileNotFoundError("File does not exist: '%s'" % filepath)

        if not os.path.isfile(filepath):
            raise IsADirectoryError("Path is a directory, not a file: '%s'" % filepath)

        if not os.access(filepath, os.R_OK):
            raise PermissionError(
                "Cannot read file: '%s' (permission denied)" % filepath
            )

        # Open file
        file_obj = open(filepath, "rb")
        return file_obj

    except Exception as e:
        # Raise generic exception with clear message to be caught by caller
        raise Exception("Error opening '%s': %s" % (filepath, str(e)))


def removeDuplicates(seq, idfun=None):
    # order preserving
    if idfun is None:

        def idfun(x):
            return x

    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result
