#!/usr/bin/python3

import io
import os
import PIL
import pytesseract
import re
import argparse
import requests
from bs4 import BeautifulSoup
# https://stackoverflow.com/a/35504626/5958455
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class Report(object):
    def __init__(self, stuid, password, data_path, emer_person, relation, emer_phone):
        self.stuid = stuid
        self.password = password
        self.data_path = data_path
        self.emer_person = emer_person
        self.relation = relation
        self.emer_phone = emer_phone
    def report(self):    
        dirname = os.path.dirname(os.path.realpath(__file__))
        data = {}
        with open(self.data_path, "r+") as f:
            for line in f:
                k, v = line.strip().split('=', 1)
                data[k] = v

        username = self.stuid
        password = self.password
        emerperson = self.emer_person
        relationship = self.relation
        emerphone = self.emer_phone
        province = data['PROVINCE']
        city = data["CITY"]
        country = data["COUNTRY"]
        is_inschool = data["IS_INSCHOOL"]

        # 1: 在校园内, 2: 正常在家
        now_status = is_inschool


        CAS_LOGIN_URL = "https://passport.ustc.edu.cn/login"
        CAS_CAPTCHA_URL = "https://passport.ustc.edu.cn/validatecode.jsp?type=login"
        CAS_RETURN_URL = "https://weixine.ustc.edu.cn/2020/caslogin"
        REPORT_URL = "https://weixine.ustc.edu.cn/2020/daliy_report"
        # Not my fault:                                  ^^


        retries = Retry(total=5,
                        backoff_factor=0.5,
                        status_forcelist=[500, 502, 503, 504])

        s = requests.Session()
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.67"
        r = s.get(CAS_LOGIN_URL, params={"service": CAS_RETURN_URL})
        x = re.search(r"""<input.*?name="CAS_LT".*?>""", r.text).group(0)
        cas_lt = re.search(r'value="(LT-\w*)"', x).group(1)
        print(cas_lt)

        r = s.get(CAS_CAPTCHA_URL)
        img = PIL.Image.open(io.BytesIO(r.content))
        pix = img.load()
        for i in range(img.size[0]):
            for j in range(img.size[1]):
                r, g, b = pix[i, j]
                if g >= 40 and r < 80:
                    pix[i, j] = (0, 0, 0)
                else:
                    pix[i, j] = (255, 255, 255)
        lt_code = pytesseract.image_to_string(img).strip()
        print(lt_code)
        data = {
            "model": "uplogin.jsp",
            "service": CAS_RETURN_URL,
            "warn": "",
            "showCode": "1",
            "username": username,
            "password": password,
            "button": "",
            "CAS_LT": cas_lt,
            "LT": lt_code,
        }
        r = s.post(CAS_LOGIN_URL, data=data)
        req = s.get("https://weixine.ustc.edu.cn/2020")
        reqt = req.text
        print(reqt)
        reqt = reqt.encode('ascii','ignore').decode('utf-8','ignore')
        soup = BeautifulSoup(reqt, 'html.parser')
        token = soup.find("input", {"name": "_token"})['value']

        data = {
            "_token": token,
            "now_address": "1",
            "gps_now_address": "",
            "now_province": province,
            "gps_province": "",
            "now_city": city,
            "gps_city": "",
            "now_country": country,
            "gps_country": "",
            "now_detail": "",
            "body_condition": "1",
            "body_condition_detail": "",
            "now_status": now_status,
            "now_status_detail": "",
            "has_fever": "0",
            "last_touch_sars": "0",
            "last_touch_sars_date": "",
            "last_touch_sars_detail": "",
            "is_danger": "0",
            "is_goto_danger": "0",
            "jinji_lxr": emerperson,
            "jinji_guanxi": relationship,
            "jiji_mobile": emerphone,
            "other_detail": "无",
            # https://twitter.com/tenderlove/status/722565868719177729
        }

        r = s.post(REPORT_URL, data=data)

        # Fail if not 200
        r.raise_for_status()

        # Fail if not reported
        assert r.text.find("上报成功") >= 0

        isFind = r.text.find("上报成功")
        if isFind >= 0:
            print("上报成功")
            return True
        else:
            return False
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='URC nCov auto report script.')
    parser.add_argument('data_path', help='path to your own data used for post method', type=str)
    parser.add_argument('stuid', help='your student number', type=str)
    parser.add_argument('password', help='your CAS password', type=str)
    parser.add_argument('emer_person', help='emergency person', type=str)
    parser.add_argument('relation', help='relationship between you and he/she', type=str)
    parser.add_argument('emer_phone', help='phone number', type=str)
    args = parser.parse_args()
    autorepoter = Report(stuid=args.stuid, password=args.password, data_path=args.data_path, emer_person=args.emer_person, relation=args.relation, emer_phone=args.emer_phone)
    count = 5
    while count != 0:
        ret = autorepoter.report()
        if ret != False:
            break
        print("Report Failed, retry...")
        count = count - 1
    if count != 0:
        exit(0)
    else:
        exit(-1)
