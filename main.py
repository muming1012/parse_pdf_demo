# This is a sample Python script.
from pdf_crop_img.service import exec_run


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


def run():
    link_path = 'https://verticalmind.oss-cn-shanghai.aliyuncs.com/new/schart/pdf/%E8%B4%A2%E9%80%9A%E8%AF%81%E5%88%B8-%E6%B1%9F%E8%8B%8F%E5%90%B4%E4%B8%AD-600200-%E6%B7%B1%E8%80%95%E8%8D%AF%E4%B8%9A%E5%BA%95%E8%95%B4%E6%B7%B1%E5%8E%9A%EF%BC%8C%E5%8C%BB%E7%BE%8E%E7%AE%A1%E7%BA%BF%E8%93%84%E5%8A%BF%E5%BE%85%E5%8F%91-230228.pdf'
    exec_run(link_path)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
