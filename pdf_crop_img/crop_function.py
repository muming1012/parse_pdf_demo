# -*- coding: utf-8 -*-
# @Author : 'Erwin'
# @File : crop_function.py
# @Software: PyCharm
import io
import re
import math

import fitz
from PIL import Image
import pdfplumber


# from src.app.cropping.paddOCR import use_paddle_ocr_func


class GetPic:
    def __init__(self, b_file_io: bytes):
        """
        初始化
        1. 初始化 file 文件为 _io.BufferedReader 类型
        2. 初始化 parser 与 doc 对象
        3. 初始化 pdf 对象与 img 对象
        """
        self.b_file_io = b_file_io

        # 创建 一个 pdfplumber 对象
        self.pdf_plumber_obj = pdfplumber.open(io.BytesIO(b_file_io)).pages
        # 打开PDF文件流信息
        self.pdf_fitz_obj = fitz.open(stream=self.b_file_io, filetype="application/pdf")
        self.pdf_right = float(self.pdf_plumber_obj[0].width)

    @staticmethod
    def pdf_convert_img(doc) -> bytes:
        """
        将单页 pdf 转换为 img 图片数据
        :param doc: 图片的doc对象
        :return: 图片内容bytes
        """
        # Matrix(zoom, zoom): zoom 图片缩放比例, type int, 数值越大分辨率越高
        """
        Deprecation: 'preRotate' removed from class 'Matrix' after v1.19.0 - use 'prerotate'. 
        Deprecation: 'getPixmap' removed from class 'Page' after v1.19.0 - use 'get_pixmap'. 
        Deprecation: 'getImageData' removed from class 'Pixmap' after v1.19.0 - use 'tobytes'.
        trans = fitz.Matrix(2, 2).preRotate(int(0))
        pix = doc.getPixmap(matrix=trans, alpha=False)
        data = pix.getImageData()
        """
        trans = fitz.Matrix(2, 2).prerotate(int(0))
        pix = doc.get_pixmap(matrix=trans, alpha=False)
        data = pix.tobytes()
        return data

    @staticmethod
    def capture_info(page, num):
        """
        解析pdf文本, 初始分析, 获取图表与来源字段
            (0, 0, 595.32, 841.92)  // pdf
            (0, 0, 960, 540)       // ppt
        """
        height = page.height
        width = page.width

        # 解析 pdf 中关键字的, 获取对应的位置点
        title_li = []
        source_li = []

        # PPT 格式
        if (height < 700) and (width > 700):
            """ PPT 格式文件需要整体进行截图 """
            words = page.extract_words(
                x_tolerance=15,
                y_tolerance=5,
                keep_blank_chars=True,
                use_text_flow=False,
            )
            point = {
                "x0": 0,
                "x1": width,
                "top": 0,
                "bottom": height,
                "y0": 0,
                "y1": height,
            }
            title_li.append(
                {"name": f'PPT_{num}_{words[0].get("text")}', "point": point}
            )
            source_li.append(
                {"name": f'PPT_{num}_{words[-1].get("text")}', "point": point}
            )

        # PDF
        else:
            # 获取的是行数据文字 [{}]
            words = page.extract_words(
                x_tolerance=15, y_tolerance=5, keep_blank_chars=True, use_text_flow=True
            )
            for w in words:
                text = w.get("text")
                if (
                    re.search(r"图\s?\d+[:：]?", text)
                    or re.search(r"表\s?\d+[:：]?", text)
                    or re.search(r"图表\s?\d+[:：]?", text)
                    or re.search(r"图表\s?\d+?[:：]?", text)
                    or re.search(r"财务[^*]", text)
                    or re.search(r"盈利预测[^*]", text)
                ):
                    # 财务表命名
                    if re.search(r"财务[^*]", text):
                        name = (
                            re.search(r"财务[^\s]+", text).group()
                            if re.search(r"财务[^\s]+", text)
                            else w.get("text")
                        )

                    elif re.search(r"盈利预测[^*]", text):
                        name = (
                            re.search(r"盈利预测[^\s]+", text).group()
                            if re.search(r"盈利预测[^\s]+", text)
                            else w.get("text")
                        )

                    else:
                        name = w.get("text")

                    title_li.append(
                        {
                            "name": name,
                            "point": {
                                "x0": w.get("x0"),
                                "x1": w.get("x1"),
                                "top": w.get("top"),
                                "bottom": w.get("bottom"),
                                "y0": height - w.get("bottom"),
                                "y1": height - w.get("top"),
                            },
                        }
                    )
                elif re.search(r"来源[:：]?", text) or re.search(r"数据来源[:：]?", text):
                    source_li.append(
                        {
                            "name": w.get("text"),
                            "point": {
                                "x0": w.get("x0"),
                                "x1": w.get("x1"),
                                "top": w.get("top"),
                                "bottom": w.get("bottom"),
                                "y0": height - w.get("bottom"),
                                "y1": height - w.get("top"),
                            },
                        }
                    )

        if len(title_li) != len(source_li):
            title_li = title_li[: len(source_li)]

        return title_li, source_li, " ".join([w.get("text") for w in words])

    @staticmethod
    def serialize_chart_point(title_li, source_li):
        """
         拿 source_li 的数据去与top进行比对, 获取对应的坐标点组
         对数据进行 左右拆分, 根据左或者右进行像素的补充
        """
        # 对 top 进行排序, 从上至下, 由小到大; 相同的top的时候, 以x0做排序, 由小到大
        title_li = sorted(
            title_li, key=lambda dic: (dic["point"]["top"], dic["point"]["x0"])
        )

        # 分别计算, 当前点位置与end中最近点的位置, 得到之后, 去除
        charts_li = []
        for i in range(len(title_li)):
            title_point = title_li[i]["point"]
            res = 1000
            end_index = 1
            for j in range(len(source_li)):
                source_point = source_li[j]["point"]
                # x0+top 定位字符的点, 分别比对title与source的点的乘方(取绝对值)
                dis = math.sqrt(
                    (title_point["x0"] - source_point["x0"]) ** 2
                    + (title_point["top"] - source_point["top"]) ** 2
                )
                if dis < res:
                    res = dis
                    end_index = j

            charts_li.append({"title": title_li[i], "source": source_li[end_index]})
            source_li.pop(end_index)

        return [
            {
                "is_change": False,
                "title": li["title"]["name"],
                "source": li["source"]["name"],
                "point": {
                    "x0": float(li["title"]["point"]["x0"]),
                    "x1": float(li["source"]["point"]["x1"]),
                    "top": float(li["title"]["point"]["top"]),
                    "bottom": float(li["source"]["point"]["bottom"]),
                    "y0": float(li["source"]["point"]["y0"]),
                    "y1": float(li["title"]["point"]["y1"]),
                },
            }
            for li in charts_li
        ]

    @staticmethod
    def judge_chart_only(chart_point_li, pdf_right, pdf_height):
        """
        函数作用:
            1. 判断图表位置点
            2. 优化图表边界值

        判断规则:
            同一平面:
                包含关系:
                    1. 图表1的上边界 大于等于 图表2的上边界 and 图表1的下边界 小于等于 图表2的下边界
                    2. 图表1的上边界 小于等于 图表2的上边界 and 图表1的下边界 大于等于 图表2的下边界

                上下关系:
                    1. 分别获得图表1, 图表2的上下边界高度之差, 取较小的高度为 high.
                        分别计算两个图表上边界差值, 下边界差值 的绝对值
                        如果两个值都大于 high 说明不在同一水平面.
        """
        offset = 10
        chart_num = len(chart_point_li)
        # 对比, 将当前的与下一组图进行比对位置.
        #   如果有在同一平面的: pop当前i与j, 将i与j添加到res_li
        for i in range(chart_num):
            # 修改过的直接跳过
            if chart_point_li[i]["is_change"]:
                continue

            # chart_point_li[i]["point"]["top"] -= offset
            # chart_point_li[i]["point"]["bottom"] += offset

            if chart_point_li[i]["point"]["top"] - offset >= 0:
                chart_point_li[i]["point"]["top"] -= offset
            if chart_point_li[i]["point"]["bottom"] + offset <= pdf_height:
                chart_point_li[i]["point"]["bottom"] += offset



                # 单独判断是最后一张图
            if i == chart_num - 1:
                # 判断最后一张的情况, 如果是flase, 那一定是没改过的, 是单张的:
                end_chart = chart_point_li[chart_num - 1]
                if not end_chart["is_change"]:
                    # end_chart["point"]["x0"] = float(0)
                    end_chart["point"]["x0"] = max(end_chart["point"]["x0"] - offset * 4, float(0))
                    end_chart["point"]["x1"] = pdf_right
                    end_chart["is_change"] = True
                continue

            chart1 = chart_point_li[i]
            left1 = chart1["point"]["x0"]  # 左边界
            # right1 = chart1["point"]["x1"]  # 右边界
            top1 = chart1["point"]["top"]  # 上边界
            bottom1 = chart1["point"]["bottom"]  # 下边界

            chart2 = chart_point_li[i + 1]
            left2 = chart2["point"]["x0"]  # 左边界
            # right2 = chart2["point"]["x1"]  # 右边界
            top2 = chart2["point"]["top"]  # 上边界
            bottom2 = chart2["point"]["bottom"]  # 下边界

            # 包含关系的同平面
            if ((top1 >= top2) and (bottom1 <= bottom2)) or (
                (top1 <= top2) and (bottom1 >= bottom2)
            ):
                # 分出左右
                if left1 < left2:
                    # 图表 chart1 在左边
                    # 图1的x0 = [pdf的最左(0) + 偏移量]
                    # chart1["point"]["x0"] = offset
                    chart1["point"]["x0"] = max(left1 - offset, offset)
                    # 图1的x1 = [图2的x0 - 偏移量]
                    chart1["point"]["x1"] = left2 - offset
                    # 图2的x0 = [图2的x0 - 偏移量]
                    chart2["point"]["x0"] = left2 - offset
                    # 图2的x1 = [pdf的最右边界 - 偏移量]
                    chart2["point"]["x1"] = pdf_right - offset
                else:
                    # 图表 chart1 在右边
                    # 图1的x0 = [x0 - 偏移量]
                    chart1["point"]["x0"] = left1 - offset
                    # 图1的x1 = [pdf 的最右边界 - 偏移量]
                    chart1["point"]["x1"] = pdf_right - offset
                    # 图2的x0 = [pdf 的最左边 + 偏移量]
                    chart2["point"]["x0"] = offset
                    # 图2的x1 = 图1的x0 - 偏移量
                    chart2["point"]["x1"] = left1 - offset

                # 置位已经修改过了
                chart2["is_change"] = True

            # 同一平面只有一个图表, 左右边界置为最边边
            else:
                # 不在同一平面内
                # 没修改过的 才进行修改
                if not chart1["is_change"]:
                    chart1["point"]["x0"] = float(0)
                    chart1["point"]["x1"] = pdf_right - offset

            chart1["is_change"] = True

        return chart_point_li

    @staticmethod
    def format_title_source(title, source):
        """
        对 title 和 source 进行处理
        """
        # 华夏 saas 不需要进行替换

        re_rules = [r"图表\s?\d+?[:：]?", r"图\s?\d+[:：]?", r"表\s?\d+[:：]?"]
        for r in re_rules:
            title = re.sub(re.compile(r), "", title)

        if len(title) > 20:
            title = title[0:20]
        title = (
            title.strip()
            .replace("（", "")
            .replace("%", "")
            .replace("）", "")
            .replace(" ", "")
        )

        if len(source) > 20:
            source = source[0:20]
        source = (
            source.replace("数据来源", "")
            .replace("资料来源", "")
            .replace("来源", "")
            .replace("：", "")
            .replace(" ", "")
            .strip()
        )

        return title, source

    def get_crops(self, coord_info, bytes_img, canvas_size):
        """
        按给定位置截取图片
        :param coord_info: 当前页中 图片坐标点位置 + 图表信息
        :param bytes_img: 当前页 pdf 的图片数据
        :param canvas_size: pdf的尺寸: tuple, (width, height)
        :return: img 的obj 对象
        """
        img_obj_li = []
        # use_paddle_flag = False
        # 获取 image 图片数据对象
        img = Image.open(io.BytesIO(bytes_img))

        # # # 如果没有坐标点, 进行第二方案执行
        # if not coord_info:
        #     try:
        #         use_paddle_flag = True
        #         coord_info = use_paddle_ocr_func(bytes_img)
        #     except Exception as e:
        #         print(" e: ", e)
        #         coord_info = []

        for dic in coord_info:
            position = dic["point"]
            # 截取的图片名称, 处理数据来源的信息
            title, source = self.format_title_source(
                dic.get("title"), dic.get("source")
            )

            # 获取调整后的截图尺寸坐标点
            img_size_tup = self.serialize_crop_coord(img.size, position, canvas_size)

            # # 获取调整后的截图尺寸坐标点
            # if not use_paddle_flag:
            #     img_size_tup = self.serialize_crop_coord(
            #         img.size, position, canvas_size
            #     )
            # else:
            #     img_size_tup = position

            # 得到截图后的图片对象
            cropped_img = img.crop(img_size_tup)
            # cropped_img.show()

            img_obj_li.append({"name": title, "source": source, "obj": cropped_img})

        return img_obj_li

    @staticmethod
    def serialize_crop_coord(pic_size, position, canvas_size):
        """
            序列化 坐标点位置, 对坐标点位置进行微调
        :param pic_size: 图片的总长度
        :param position: 要截取的位置, tuple, (y1, y2)
        :param canvas_size: 图片为pdf时的尺寸, tuple, (0, 0, width, height)

        Python 成像库使用笛卡尔像素坐标系，左上角为 (0,0)
        坐标通常作为 2 元组 (x, y) 传递给库。 首先给出左上角。
        例如，一个覆盖所有 800x600 像素图像的矩形被写为 (0, 0, 800, 600)。
        """
        left = pic_size[0] * ((position["x0"]) / canvas_size[2])
        upper = pic_size[1] * ((position["top"]) / canvas_size[3])
        right = pic_size[0] * ((position["x1"]) / canvas_size[2])
        lower = pic_size[1] * ((position["bottom"]) / canvas_size[3])
        capture_range = (left, upper, right, lower)

        return capture_range

    @staticmethod
    def rid_exception_chart(position_li):
        """
        异常图表坐标处理
            - 剔除尺寸过小的图片
        """
        reference_value = 50
        return [
            position
            for position in position_li
            if (
                abs(position["point"]["bottom"] - position["point"]["top"])
                > reference_value
            )
        ]

    def img_convert_bytes(self, cropped_img):
        img_byte_arr = io.BytesIO()
        cropped_img.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()

    def pdf_extract_point(self, pdf_obj, pgn):
        """
        对 pdf 进行处理, 获取图表的坐标点信息
        """
        # 获取关键词句信息 + word文本内容
        title_li, source_li, word_texts = self.capture_info(pdf_obj, pgn)

        # 对于上下节点信息进行拼接, 获取图表的具体位置信息
        charts_point_li = self.serialize_chart_point(title_li, source_li)

        # 判断同一平面是否有其他图表, 对坐标点位置进行补全
        # position_li = self.judge_chart_only(charts_point_li, self.pdf_right)
        position_li = self.judge_chart_only(charts_point_li, float(self.pdf_plumber_obj[pgn].width), float(self.pdf_plumber_obj[pgn].height))

        # 返回剔除异常的图表坐标点
        return self.rid_exception_chart(position_li), word_texts

    def pdf_resolver_img(self, pgn):
        """
        对pdf进行转换
            1. 获取 img 数据体
            2. 获取 pdf 数据体
            3. 聚合处理
        """
        # 将当前的pdf页数据 转换为 PNG 图片
        bytes_img = self.pdf_convert_img(self.pdf_fitz_obj[pgn])

        # 对 pdf 对象进行处理, 获取pdf中图表的位置点信息 + 文本信息
        chart_coord_li, word_texts = self.pdf_extract_point(
            self.pdf_plumber_obj[pgn], pgn
        )

        # 操作截取图片, 获取图片对象列表
        return (
            self.get_crops(
                chart_coord_li, bytes_img, self.pdf_plumber_obj[pgn].layout.bbox
            ),
            word_texts,
        )

    def exec_run(self, pgn, img_obj_li, text_li):
        try:
            res_dic = self.pdf_resolver_img(pgn)
            img_obj_li.extend(res_dic[0])
            # 取 pdf 文字
            text_li.append(res_dic[1])
        except Exception as e:
            print(f"PDF 文件的第 {pgn} 页解析异常...", e)

    def main(self):
        """
        1. 将pdf整体转换为一张张图片
        2. 去识别 pdf 中的图片位置
        3. 根据 pdf 中位置坐标, 去图片中截取
        4. 返回截取的图片数据体  [{},{},...]
            {name: 图片名称, obj: img对象(需转换为bytes类型上传阿里云)}

        return:
            img_obj_li: [{}, {}] 图表对象列表
            text_li: [str, str] pdf 报告内容
            page_num: [int] pdf 页码
        """
        img_obj_li = []
        text_li = []

        self.exec_run(9, img_obj_li, text_li)

        # 将所有的 pdf 转换为图片
        # for pgn in range(self.pdf_fitz_obj.pageCount):
            # try:
            #     res_dic = self.pdf_resolver_img(pgn)
            #     img_obj_li.extend(res_dic[0])
            #     # 取 pdf 文字
            #     text_li.append(res_dic[1])
            # except Exception as e:
            #     print("PDF 文件的第 {pgn} 页解析异常...", e)

        return {
            "img_obj_li": img_obj_li,
            "text_li": text_li,
            "page_num": self.pdf_fitz_obj.pageCount,
        }

