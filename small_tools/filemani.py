import os

def get_all_suffixs_files(root: str, suffixs: list) -> tuple[list]:
    """获取目录下指定后缀文件名

    Parameters
    ---
    `root`: Absolute path of folder.

    `suffixs`: Suffixs to select.

    Return
    ---
    `namelist`: List of file name.

    `abspathlist`: List of absolute path of files.
    """
    name_lst, path_lst = [], []
    for tmproot, _, tmppaths in os.walk(root):
        if tmproot == root:
            for tmppath in tmppaths:
                for _ in filter(tmppath.endswith, suffixs):
                    name_lst.append(tmppath)
                    path_lst.append("%s/%s" % (root, tmppath))
    return name_lst, path_lst
