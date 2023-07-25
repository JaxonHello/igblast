from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import logging


# 基础设置-------------------------------------------------

# 设置 输出日志 级别为INFO以上
logging.basicConfig(level=logging.INFO)
# 设置 读取文件夹
# ：'您可以将你获得的html文件放在data/html_page文件夹中'
html_dic = "data/html_page"


# 方法定义-------------------------------------------------
def html_read(html_file):
    '''
    this function is to read html file
    :param html_file: html file relative path
    :return: html page in str
    '''
    # 得到文件的相对路径 //os.path.join --> type: str
    html_path = os.path.join(html_dic, html_file)
    # 读取文件流 //mode='r'用于仅仅读取文件
    o = open(html_path, mode='r', encoding='utf-8')
    # 文件流内容读取
    html_text = o.read()
    # 关闭读取
    o.close()
    return html_text


def index_list(html):
    """
    find how many Query items in the search results
    :param html: origin html
    :return: Query number as a num list
    """
    str_list = re.findall('<a href=#index(.*?)>Query=lcl', html, re.S)
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
    result = re.search(f'<a name=index{index}></a>.*?<b>Query=</b>(.*?)<hr>', html, re.S)
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
    find text information of html page which is not <table> label
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
    seqs = re.findall('EntrezView" >(.*?)</a>germline gene', html, re.S)
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


def table_to_dataframe(html):
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
    df_table = table_to_dataframe(html)
    df_seq = sequences_df(html)
    list.append(df_info)
    list.append(df_table)
    list.append(df_seq)
    df_html = pd.concat(list, axis=1)
    return df_html


def sequences_get(html):
    # 定位到基因序列信息
    center_content = re.findall('<CENTER>(.*?)Lambda', html, re.S)[0]
    other_info = re.findall('<a name.*?</span>', html, re.S)
    # left_info = center_content.replace(other_info[0], '')
    cc = center_content
    for item in other_info:
        left_info = cc.replace(item, '')
        cc = left_info
    # 得到只含序列的信息
    cc = cc.replace('lcl|Query_2_reversed', '')
    cc = cc.replace('<b><FONT color="green">Alignments</FONT></b></CENTER>', '')
    # cc = cc.replace('&lt;', '<---').replace('&gt;', '--->')
    # 找到所有的碱基对
    base = re.findall('[ATCGN]+', cc, re.S)
    gene = ''
    for b in base:
        if len(b) > 2:
            gene += b
    # 将基因的简介信息拼起来
    gene_name = ''
    for line in cc.splitlines():
        if re.search('(?:&gt;|&lt;)', line):
            gene_name += line.strip()
    gene_name = gene_name.replace('&lt;', '<').replace('&gt;', '>')
    # 找到所有的蛋白质
    found_next_line = False
    protein = ''
    for line in cc.splitlines():
        if found_next_line:
            protein += ' ' + line.strip() + ' '
            found_next_line = False
        if re.search('(?:&gt;|&lt;)', line):
            found_next_line = True
    l = []
    l.append(gene_name)
    l.append(gene)
    l.append(protein)
    return l


def sequences_process(list):
    dataframe = pd.DataFrame()
    # 获得基因和蛋白质的list
    gene_all_seq = list[1]
    pro_all_seq = list[2]
    # 得到分割的gene名字的list
    gene_list = re.split(r'(?<=>)', list[0])
    gene_list.pop()
    # 创建空的基因和蛋白质序列的list
    gene_seq_list = []
    pro_seq_list = []
    # 按照基因名字的长度进行分割得到片段list
    for gene in gene_list:
        length = len(gene)
        gene_seq = gene_all_seq[:length]
        gene_seq_list.append(gene_seq)
        pro_seq = pro_all_seq[:length]
        pro_seq_list.append(pro_seq)
        gene_all_seq = gene_all_seq[length:]
        pro_all_seq = pro_all_seq[length:]
    # 创建基因名字的序列
    name_list = []
    for gene in gene_list:
        gene_name = re.search('[\w\d]+-[\w\d]+', gene)
        name_list.append(gene_name.group())
    # 添加list到dataframe
    dataframe[len(dataframe.T)] = name_list
    dataframe[len(dataframe.T)] = gene_seq_list
    dataframe[len(dataframe.T)] = pro_seq_list
    return dataframe


def sequences_df(html):
    seq_list = sequences_get(html)
    seq_df = sequences_process(seq_list)
    seq_df.loc[-1] = ['', 'gene_seq', 'pro_seq']
    seq_df.index = seq_df.index + 1
    seq_df = seq_df.sort_index()
    seq_df = df_D_reduction(seq_df)
    return seq_df


# 程序运行 ----------------------------------------------
# html_content = html_read('igblast.html')
# html_01 = html_separation_by_index(html_content, 1)


logging.info("正在爬取网页")
html = html_read('igblast.html')
logging.info("爬取网页成功")
logging.info("正在解析网站")
query_num = index_list(html)
print(query_num)
list = []
for i in query_num:
    index_html = html_separation_by_index(html, i)
    index_df = html_to_dataframe(index_html)
    list.append(index_df)
print(list)
df = pd.concat(list)
df.index = query_num
logging.info("解析网站成功")
logging.info("开始写入excel")
writer = pd.ExcelWriter("result/excel.xlsx")
df.to_excel(writer, sheet_name='sheet0')
writer.close()
logging.info("成功保存excel")







