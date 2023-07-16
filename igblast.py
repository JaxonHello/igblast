from bs4 import BeautifulSoup
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import logging


logging.basicConfig(level=logging.INFO)
# 请输入您的项目文件的绝对路径 --> 在此修改！！
FILE_PATH = '/Users/jaxonhe/Desktop/30-369334923.fasta'


def scrape_html_selenium(file_path):
    option = webdriver.ChromeOptions()
    option.add_argument('headless')
    driver = webdriver.Chrome(options=option)
    driver.get("https://www.ncbi.nlm.nih.gov/igblast/")
    uploeder = driver.find_element(By.ID, "upl")
    uploeder.send_keys(file_path)
    button = driver.find_element(By.XPATH, '//*[@value="Search"]')
    button.click()
    html = driver.page_source
    driver.quit()

    return html


def index_list(html):
    """
    find how many Query items in the search results
    :param html: origin html
    :return: Query number as a num list
    """
    str_list = re.findall('<a href="#index(.*?)">Query=lcl', html, re.S)
    num_list = []
    for str in str_list:
        num_list.append(int(str))
    return num_list


def html_separation_by_index(html, index):
    """
    separate the origin html to specific Query index html
    :param html: origin html
    :param index: Query number index
    :return: Separated html page
    """
    result = re.search(f'<a name="index{index}"></a>.*?<b>Query=</b>(.*?)<hr>', html, re.S)
    index_html = result.group(1)
    return index_html


def df_D_reduction(df):
    """
    To reduce the dimension of dataframe from 2D to 1D
    :param df: origin 2D dataframe whose index is [a, b]
    :return: 1D dataframe whose column is a_b
    """
    # 设置行名与列名
    df.columns = df.iloc[0, :]
    df.index = df.iloc[:, 0]
    df = df.drop(['']).drop([''], axis=1)
    # 降维
    df = pd.DataFrame(data=df.stack()).T
    # 将tuple的列名设为字符连接形式
    df.columns = [(column[0]+'_'+column[1]) for column in df.columns.values.tolist()]
    return df


def info_to_dataframe(html):
    """
    find text infomation of html page
    :param html: html page
    :return: dataframe
    """
    l = []
    df = pd.DataFrame()
    name = html.splitlines()[0].strip()
    result_length = re.search('Length=(\d+)', html, re.S)
    Length = int(result_length.group(1))
    list = [name, Length]
    df0 = pd.DataFrame(data=list).T
    df0.columns = ["Query", "Length"]
    l.append(df0)
    seqs = re.findall('EntrezView">(.*?)</a>germline gene', html, re.S)
    df[len(df.T)] = seqs
    scores = re.findall('"EntrezView".*?germline gene.*?>(.*?)</a>', html, re.S)
    scores = [round(float(score), 1) for score in scores]
    df[len(df.T)] = scores
    E_values = re.findall('"EntrezView".*?</a>germline gene.*?</a>(.*)', html)
    E_values = [float(e.strip()) for e in E_values]
    df[len(df.T)] = E_values
    df.loc[0] = ['', 'score', 'E values']
    df = df_D_reduction(df)
    l.append(df)
    l_df = pd.concat(l, axis=1)
    return l_df


def html_table_to_dataframe(html):
    """
    find all the table in the html page
    :param html: html page
    :return: dataframe
    """
    soup = BeautifulSoup(html, 'lxml')
    l = []
    # 找到每一个table
    for table in soup.findAll('table'):
        # 准备总的空dataframe
        df = pd.DataFrame()
        # 对每一个table进行操作
        for row in table.findAll('tr'):
            list = []
            for td in row.findAll('td'):
                td_str = str(td).lstrip('<td>').rstrip('</td>').strip()
                # 如果是数字的话，将str转换为数字
                if re.search('^-?\d+(\.\d+)?$', td_str):
                    td_str = round(float(td_str), 1)
                list.append(td_str)
            # 在此处对df进行变形即可：
            df[len(df.T)] = list
        # 将每个table转换的dataframe转入总的list---l
        if df.iloc[0, 0] == '':
            df = df_D_reduction(df.T)
        else:
            df = df.T
            df.columns = df.iloc[0, :]
            df = df.drop(index=0)
            df.loc[0] = df.loc[1]

        l.append(df)
    l_df = pd.concat(l, axis=1).drop(index=1)
    return l_df


def html_to_dataframe(html):
    """
    find all the information of the igblast html message
    :param html:
    :return:
    """
    #1.添加整个excel表的表头（第一行），确定要展示的信息
    #[id, Query, Length, ......]
    list = []
    df_info = info_to_dataframe(html)
    df_table = html_table_to_dataframe(html)
    list.append(df_info)
    list.append(df_table)
    df_html = pd.concat(list, axis=1)
    return df_html


def main():
    # f = open('igblast.html', encoding='utf-8')
    # html = f.read()
    # f.close()
    logging.info("正在爬取网页")
    html = scrape_html_selenium(FILE_PATH)
    logging.info("爬去网页成功")
    logging.info("正在解析网站")
    query_num = index_list(html)
    list = []
    for i in query_num:
        index_html = html_separation_by_index(html, i)
        index_df = html_to_dataframe(index_html)
        list.append(index_df)
    df = pd.concat(list)
    df.index = query_num
    logging.info("解析网站成功")
    logging.info("开始写入excel")
    writer = pd.ExcelWriter("result/excel.xlsx")
    df.to_excel(writer, sheet_name='sheet0')
    writer.close()
    logging.info("成功保存excel")


if __name__ == '__main__':
    main()