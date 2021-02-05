# -*- coding: utf-8 -*-
# @Author: yuzhou
# @Date:   2021-02-03 11:31:37
# @Last Modified by:   yuzhou
# @Last Modified time: 2021-02-05 15:15:17
#
import xml.etree.ElementTree as ET
import os
import sys
import requests
import json
import urllib.parse
from urllib.parse import urlparse
import socket


class Jmx(object):
    """解析curl生成jmx文件"""
    # 1.通过在线工具解析curl 生成 json格式文件
    # 2.解析jmx文件，将 json格式的参数塞入jmx文件
    # 目前支持的请求组合：
    # a. get + queries
    # b. post + json
    # 文件流不支持，其他的，待完善

    def __init__(self):
        super(Jmx, self).__init__()
        self.xmlFilePath = os.path.abspath("resource/jmxTemp.jmx")
        self.domain = ''
        self.protocol = ''
        self.path = ''
        self.method = ''
        self.headers = {}
        self.cookies = {}
        self.collection_prop = ''
        self.data = {}

        try:
            self.tree = ET.parse(self.xmlFilePath)
            # 获取根节点
            root = self.tree.getroot()
            # 获取 domain protocol path method
            self.domain = root.findall(".//*[@name='HTTPSampler.domain']")[0]
            self.protocol = root.findall(".//*[@name='HTTPSampler.protocol']")[0]
            self.path = root.findall(".//*[@name='HTTPSampler.path']")[0]
            self.method = root.findall(".//*[@name='HTTPSampler.method']")[0]
            self.headers = root.findall(".//*[@name='HeaderManager.headers']")[0]
            self.cookies = root.findall(".//*[@name='CookieManager.cookies']")[0]
            # print('headers:')
            # print(self.headers.attrib)
            # print('cookies:')
            # print(self.cookies.attrib)

            # http请求sample
            http_sampler = root.findall(".//*[@testclass='HTTPSamplerProxy']")[0]
            # queries参数集合
            self.collection_prop = http_sampler.findall(".//*[@name='Arguments.arguments']")[0]
            # body json
            self.body_json = http_sampler.findall(".//*[@name='Argument.value']")[0]

        except Exception as e:
            print('parse .xml fail')
            raise e

    def json_to_jmx(self, json_dict):
        '''[json转换成 jmx文件]
        Arguments:
            json_dict {[dict]} -- [
            json 模板：
            {
                "url":"",
                "raw_url":"",
                "method":"get",
                "cookies":{
                },
                "headers":{
                },
                # queries参数 不一定有
                "queries":{
                },
                # post body json参数 不一定好有 
                "data":{
                }
            }
            ]
        '''
        url = json_dict['url']
        res = urllib.parse.urlparse(url)
        # 设置到jmx
        self.domain.text = res.hostname
        self.protocol.text = res.scheme
        self.path.text = res.path
        self.method.text = json_dict['method'].upper()
        # 设置headers
        heasers = json_dict['headers']
        for key, value in heasers.items():
            str = '''
                <elementProp name="" elementType="Header">
                    <stringProp name="Header.name">''' + key + '''</stringProp>
                    <stringProp name="Header.value">''' + value + '''</stringProp>
                </elementProp>
                '''
            new_params = ET.fromstring(str)
            self.headers.append(new_params)
        # 设置cookie
        cookies = json_dict['cookies']
        for key, value in cookies.items():
            str = '''
                <elementProp name="''' + key + '''" elementType="Cookie" testname="''' + key + '''">
                    <stringProp name="Cookie.value">''' + value + '''</stringProp>
                    <stringProp name="Cookie.domain"></stringProp>
                    <stringProp name="Cookie.path"></stringProp>
                    <boolProp name="Cookie.secure">false</boolProp>
                    <longProp name="Cookie.expires">0</longProp>
                    <boolProp name="Cookie.path_specified">true</boolProp>
                    <boolProp name="Cookie.domain_specified">true</boolProp>
                </elementProp>
                '''
            new_params = ET.fromstring(str)
            self.cookies.append(new_params)

        # 设置query参数
        if 'queries' in json_dict.keys():
            querys = json_dict['queries']
            for key, value in querys.items():
                str = '''
                    <elementProp elementType="HTTPArgument" name="''' + key + '''">
                        <boolProp name="HTTPArgument.always_encode">false</boolProp>
                        <stringProp name="Argument.value">''' + value + '''</stringProp>
                        <stringProp name="Argument.metadata">=</stringProp>
                        <boolProp name="HTTPArgument.use_equals">true</boolProp>
                        <stringProp name="Argument.name">''' + key + '''</stringProp>
                    </elementProp>
                    '''
                new_params = ET.fromstring(str)
                self.collection_prop.append(new_params)

        # 设置body json参数
        if 'data' in json_dict.keys():
            data_keys = json_dict['data'].keys()
            # 这里很奇怪，json参数放在key上
            j_value = {}
            for key in data_keys:
                j_value = key
            self.body_json.text = j_value

        # 输出转换文件
        outXmlFilePath = os.path.abspath("resource/outJmxTemp.jmx")
        f = open(outXmlFilePath, 'r+')
        f.truncate()
        f.close()
        self.tree.write(outXmlFilePath, 'UTF-8')

    def curl_to_json(self, curl_txt):
        '''[curl转json]
        Arguments:
            curl_txt {[str]} -- [curl命令]
        Returns:
            [dict] -- [解析请求的json_dict]
        '''
        # 先用在线工具实现 cookie不知道会不会失效
        cookies = {
            'slim_session': '%7B%22slim.flash%22%3A%5B%5D%7D',
            'uuid': 'fc70cbf8-f122-4bc8-cbf9-2cbccab99051',
            'Hm_lvt_0fba23df1ee7ec49af558fb29456f532': '1612330224',
            'Hm_lpvt_0fba23df1ee7ec49af558fb29456f532': '1612330224',
        }
        headers = {
            'Host': 'tool.lu',
            'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'sec-ch-ua-mobile': '?0',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://tool.lu',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://tool.lu/curl/',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        data = {
            "command": curl_txt,
            "target": "json"
        }
        response = requests.post('https://tool.lu/curl/ajax.html', headers=headers, cookies=cookies, data=data)
        res = response.json()['code']
        json_dict = json.loads(res)
        # 把 cookie设置到headers里面去
        cookie_value = ''
        for key, value in json_dict['cookies'].items():
            cookie_value = cookie_value + key + '=' + value + ';'
        cookie_value = cookie_value[:-1]
        json_dict['headers']['Cookie'] = cookie_value
        print(json.dumps(json_dict))
        return json_dict


if __name__ == '__main__':
    jmx = Jmx()
    # get + querys
    # curl_txt = '''curl -H 'Host: jinrong.test.zcygov.cn' -H 'Accept: application/json, text/plain, */*' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36' -H 'X-Requested-With: XMLHttpRequest' -H 'Referer: http://jinrong.test.zcygov.cn/luban/test/loan' -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' -H 'Cookie: _zcy_log_client_uuid=f9f60640-e5ab-11ea-8acb-b76fd9a095b1; UM_distinctid=1742065d9c3132-0bad89755f6d4d-31607305-13c680-1742065d9c4250; gr_user_id=7fa51be3-c9f3-4036-904c-1caed9545c21; districtCode=339900; districtName=%E6%B5%99%E6%B1%9F%E7%9C%81%E6%9C%AC%E7%BA%A7; districtCode=993300; districtName=%E5%9F%B9%E8%AE%AD%E6%BC%94%E7%A4%BA%E7%9C%81' --compressed 'http://jinrong.test.zcygov.cn/api/loan/anonymous/front/desk/channel/summary/list?distCode=&timestamp=1612504120'''
    # post + None cookie对象是多余的，把cookie组装到headers里面去了
    # curl_txt = '''curl -H 'Host: middle.test.zcygov.cn' -H 'User-Agent: python-requests/2.23.0' -H 'Accept: */*' -H 'Cookie: SESSION=NDMzZWUzMzAtZGM4Zi00ZmYwLWFiNDYtNjNlYTA0Y2M1ZWNj; institution_id=1; platform_code=zcy; uid=10007000000; user_type=99; wsid=1#1612505452991' --data-binary "" --compressed 'http://middle.test.zcygov.cn/api/synlogin/suspendedceiling/user'''
    # post + json
    curl_txt = '''curl -H 'Host: middle.test.zcygov.cn' -H 'User-Agent: python-requests/2.23.0' -H 'Accept: */*' -H 'Cookie: SESSION=NDYxMDk2MGYtN2I2NC00ZmIxLWFmYTQtYmM2NmU4M2U5MDhh; institution_id=1; platform_code=zcy; uid=10007000000; user_type=99; wsid=1#1612507255326' -H 'Content-Type: application/json' --data-binary '{"types": 1, "businessCategory": 1, "category": 1, "channel": {"id": 1, "channelCode": "ABC330106001", "channelName": "\u4e2d\u56fd\u519c\u4e1a\u94f6\u884c\u6d59\u6c5f\u7701\u5206\u884c", "noWordLogo": "https://demo-open-doc.oss-cn-hangzhou.aliyuncs.com/1089PT/null/1/20207/a41d6c6a-b1be-4c6b-baf2-22a20774a977", "channelId": 1}, "process": 1, "code": "1yuzhou_code20210205144055", "num": "1yuzhou_num20210205144055", "name": "1yuzhou_name20210205144055", "subtitle": "\u526f\u6807\u9898", "description": "\u4ea7\u54c1\u63cf\u8ff0", "smallImage": {"fileId": "1089PT/null/1/202011/28a8c48e-6d0e-44a3-9796-55d92bcdc69c", "fileType": "image/png", "name": "salt.png"}, "bigImage": {"fileId": "1089PT/null/1/202011/ff194f69-8348-49a4-801f-cbc25e33a24e", "fileType": "image/png", "name": "salt.png"}, "note": "\u6ce8\u610f\u4e8b\u9879", "problem": "\u5e38\u89c1\u95ee\u9898", "loop": true, "repayment": [1], "repaymentCycle": {"type": 1, "val": null}, "repaymentDay": 1, "overdue": {"rateNum": null, "type": 1}, "defaultRepayment": {"rateNum": null, "type": 1}, "applyLimit": 199, "terminalType": [1], "userType": ["02", "0201", "020101", "0202"], "joinMode": 1, "modelHead": 1, "modelYear": 1, "creditLeft": 100, "creditRight": 100000000, "qrCode": {}, "business": [{"industryId": 50897, "industryCode": "001", "industryName": "\u9879\u76ee\u91c7\u8d2d", "codeType": null, "tagList": [7, 8, 12], "instanceList": null, "logoName": "poki", "shortName": "\u9879\u76ee\u91c7\u8d2d\t", "domain": "staging.zcygov.cn", "appDomain": null, "industryStatus": 2, "instanceId": 1231, "instanceCode": "XMCG", "districtCodeList": null, "instanceName": "\u9879\u76ee\u91c7\u8d2d", "status": 2, "isEnabled": 1, "platformLevel": 0, "agreementSupervision": null, "searchShortName": "", "applicationScope": "1,1,1,0", "limitPurchase": 0, "applicationTags": [12], "districtIsAll": 0, "districtCodes": ["150302"], "districtCodesDesc": "\u6d77\u52c3\u6e7e\u533a"}], "dataPushBusiness": [], "supplierList": [], "projectDistrictDetail": {"isAll": true}, "supplierDistrictDetail": {"isAll": true, "supplierDistrict": []}, "enterpriseBusinessDistrict": {"isAll": true, "supplierDistrict": []}, "personApplyAddress": null, "productCondition": [{"id": 55, "name": "nicaicai\u6761\u4ef6", "isSystem": false, "remark": " nicaicai\u5907\u6ce8", "createTime": 1591760990000, "sort": 1, "creator": null, "updator": null, "updateTime": null}], "productProtocol": [{"node": 1, "name": "\u653f\u91c7\u4e91\u878d\u8d44\u4fe1\u606f\u670d\u52a1\u534f\u8bae", "types": 1}], "productRateList": [{"deadLine": 12, "monthRate": 2.4, "channelName": "\u4e2d\u56fd\u519c\u4e1a\u94f6\u884c\u6d59\u6c5f\u7701\u5206\u884c"}], "productTollList": [{"types": {"id": 1, "name": "\u6280\u672f\u670d\u52a1\u8d39"}, "node": 1}], "basisId": 2824, "status": 3}' --compressed 'http://middle.test.zcygov.cn/api/loan/product/channel'''
    json_dict = jmx.curl_to_json(curl_txt)
    jmx.json_to_jmx(json_dict)
