# -*- coding: utf-8 -*-
# @Author : 'Erwin'
# @File : service.py.py
# @Software: PyCharm
from pdf_crop_img.crop_function import GetPic
from pdf_crop_img.getPdf import get_file_func


def corp_img_execute(file_io):
    """
            进行pdf 的切图转换
            """
    # 进行切图转换: 获取 pdf 中的图片
    try:
        pic_cls = GetPic(file_io.read())
        crop_dic_data = pic_cls.main()
        return crop_dic_data

    except Exception as e:
        raise ValueError(f"解析pdf失败, 请检查pdf文件是否正常")


def execute_pdf2img(file_io):
    """
    TODO 待重构...
    1. pdf中截取图片, 获取所有的图片的二进制数据
    2. 上传二进制数据至阿里云oss
    3. 返回 阿里云oss 的文件连接给web端

    通过 choice_all 参数控制获取的参数值, 后续统一获取全部(不止切图)
    """
    # 2. 进行 pdf 的切图服务, 获取数据信息
    crop_dic_data = corp_img_execute(file_io)
    img_obj_li = crop_dic_data.pop("img_obj_li")

    # if not img_obj_li:
    #     raise ValueError(f"解析pdf失败, 未能识别图片")

    return img_obj_li


def exec_run(link_path):
    try:
        file_io = get_file_func(link_path)
    except Exception as e:
        raise ValueError(f"获取oss数据异常: {e}")

    return execute_pdf2img(file_io)
