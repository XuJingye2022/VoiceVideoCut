"""
网上不少图片格式为`.webp`

默认程序无法处理

因此在类初始化时，直接进行转换。
"""


import os
from PIL import Image, ImageOps

def convert_webp2jpg(webp_path):
    """
    将`.webp`文件，转化为`.jpg`文件，不保留原图。
    """
    image = Image.open(webp_path)
    image = ImageOps.exif_transpose(image)
    path, _ = os.path.splitext(webp_path)
    dstImagePath = path + '.jpg'
    image.save(dstImagePath)
    print('%s ---> %s' % (webp_path, dstImagePath))
    os.remove(webp_path)

if __name__ == '__main__':
    webp_path = r"C:\Users\徐景晔\Pictures\搞笑图片\4bed2e738bd4b31c2942b40e7cb273789f2ff8f1.webp"
    convert_webp2jpg(webp_path)