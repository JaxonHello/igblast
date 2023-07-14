import time

from bs4 import BeautifulSoup
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

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


def info_to_dataframe(html):
    l = []
    df = pd.DataFrame()
    list = []
    name = html.splitlines()[0].strip()
    list.append(name)
    result_length = re.search('Length=(\d+)', html, re.S)
    Length = result_length.group(1)
    list.append(f'Length={Length}')
    df0 = pd.DataFrame(data=list).T
    l.append(df0)
    seqs = re.findall('EntrezView" >(.*?)</a>germline gene', html, re.S)
    df[len(df.T)] = seqs
    scores = re.findall('"EntrezView".*?germline gene.*?>(.*?)</a>', html, re.S)
    df[len(df.T)] = scores
    E_values = re.findall('"EntrezView".*?</a>germline gene.*?</a>(.*)', html)
    E_values = [e.strip() for e in E_values]
    df[len(df.T)] = E_values
    df.loc[0] = ['Sequences producing significant alignments', 'score(bits)', 'E values']
    l.append(df)
    l_df = pd.concat(l)
    return l_df


def html_table_to_dataframe(html):
    soup = BeautifulSoup(html, 'lxml')
    l = []
    for table in soup.findAll('table'):
        df = pd.DataFrame()
        for row in table.findAll('tr'):
            list = []
            for td in row.findAll('td'):
                td_str = str(td).lstrip('<td>').rstrip('</td>').strip()
                # if re.match('^[1-9]\d*\.\d*|0\.\d*[1-9]\d*$', td_str):
                #     td_str = float(td_str)
                list.append(td_str)
            df[len(df)] = list
        l.append(df.T)
    l_df = pd.concat(l)
    return l_df


def html_to_dataframe(html):
    list = []
    df_info = info_to_dataframe(html)
    df_table = html_table_to_dataframe(html)
    list.append(df_info)
    list.append(df_table)
    df_html = pd.concat(list)
    return df_html


def main():
    # f = open('igblast.html', encoding='utf-8')
    # html = f.read()
    # f.close()
    html = scrape_html_selenium(FILE_PATH)
    query_num = index_list(html)
    writer = pd.ExcelWriter("result/excel.xlsx")
    for i in query_num:
        index_html = html_separation_by_index(html, i)
        index_df = html_to_dataframe(index_html)
        index_df.to_excel(writer, sheet_name=f'sheet{i}', index=None)
    writer.close()


if __name__ == '__main__':
    main()
