import os
from multipledispatch import dispatch


@dispatch(str, str)
def get_all_files_with_extensions(root: str, ext: str) -> tuple[list]:
    """从文件夹中获得指定扩展名`ext`的文件列表

    返回文件名列表和文件绝对路径列表
    """
    return get_all_files_with_extensions(root, [ext])


@dispatch(str, list)
def get_all_files_with_extensions(root: str, ext: list[str]) -> tuple[list]:
    """从文件夹中获得指定扩展名`ext`的文件列表.

    返回文件名列表和文件绝对路径列表
    """
    name_lst, path_lst = [], []
    for tmproot, _, tmppaths in os.walk(root):
        if tmproot == root:
            for tmppath in tmppaths:
                for _ in filter(tmppath.endswith, ext):
                    name_lst.append(tmppath)
                    path_lst.append("%s/%s" % (root, tmppath))
    return name_lst, path_lst


def change_file_extension(s: str, new_ext: str):
    """Change file extension of a file name or path.

    Args:
        s (str): File name or path.
        new_ext (str): New file extension.

    Returns:
        str: New file name or path.
    """
    name, _ = os.path.splitext(s)
    if new_ext.startswith("."):
        return name + new_ext
    else:
        return name + "." + new_ext


def add_suffix_to_filename(s: str, suffix: str):
    fname, ext = os.path.splitext(s)
    return fname + suffix + ext
