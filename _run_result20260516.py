# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.path.insert(0, r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')

import json

RESULT = {
    "race_name": "新潟大賞典 GⅢ",
    "venue": "新潟",
    "race_no": 11,
    "results": [
        {"rank": 1,  "horse_no": 3,  "horse_name": "グランディア",      "popularity": 7,  "odds": 15.3},
        {"rank": 2,  "horse_no": 11, "horse_name": "バレエマスター",    "popularity": 12, "odds": 49.7},
        {"rank": 3,  "horse_no": 9,  "horse_name": "フクノブルーレイク","popularity": 9,  "odds": 18.8},
        {"rank": 4,  "horse_no": 6,  "horse_name": "ドゥラドーレス",    "popularity": 1,  "odds": 2.5},
        {"rank": 15, "horse_no": 15, "horse_name": "シュガークン",      "popularity": 2,  "odds": 7.0},
    ],
    "payouts": {
        "tansho":   {"combo": "3",     "amount": 1530},
        "umaren":   {"combo": "3-11",  "amount": 25100},
        "sanrentan":{"combo": "3-11-9","amount": 810010},
        "sanrenpuku":{"combo":"3-9-11","amount": 109690},
    }
}

sys.argv = ['result_checker.py', '--result', json.dumps(RESULT, ensure_ascii=False)]
exec(open('result_checker.py', encoding='utf-8').read())
