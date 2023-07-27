import os
from multipledispatch import dispatch

@dispatch(str, str)
def get_all_suffixs_files(root: str, suffix: str) -> tuple[list]:
    """Obtain the specified suffix file name under the directory.

    Args:
        root (str): Root directory to find files, excluding subfolders.
        suffix (str): One suffix to match.

    Returns:
        tuple[list]: Matched file names and corresponding absolute paths.
    """
    get_all_suffixs_files(root, [suffix])

@dispatch(str, list)
def get_all_suffixs_files(root: str, suffixs: list) -> tuple[list]:
    """Obtain the specified suffix file name under the directory.

    Args:
        root (str): Root directory to find files, excluding subfolders.
        suffixs (list): Suffixs to find.

    Returns:
        tuple[list]: Matched file names and corresponding absolute paths.
    """
    name_lst, path_lst = [], []
    for tmproot, _, tmppaths in os.walk(root):
        if tmproot == root:
            for tmppath in tmppaths:
                for _ in filter(tmppath.endswith, suffixs):
                    name_lst.append(tmppath)
                    path_lst.append("%s/%s" % (root, tmppath))
    return name_lst, path_lst

def change_suffix(s: str, new_post_fix: str):
    """Change the suffix of a file name or path.

    Args:
        s (str): File name or path.
        new_post_fix (str): New file suffix.

    Returns:
        str: New file name or path.
    """
    lst = s.split(".")
    lst[-1] = new_post_fix
    return ".".join(lst)