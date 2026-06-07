# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')

# 条件C（新潟10R）購入候補を保存
sys.argv = ['result_checker.py', '--save',
    '{"venue":"新潟","date":"20260523","candidates":['
    '[10,1,"サイレントグルーヴ","条件C",44.6],'
    '[10,3,"エコログロス","条件C",72.9],'
    '[10,4,"ドーギッド","条件C",26.2],'
    '[10,6,"マルチライジングハース","条件C",39.3],'
    '[10,12,"フォーグッド","条件C",23.8],'
    '[10,13,"ローンウルフ","条件C",107.4]'
    ']}']
exec(open('result_checker.py', encoding='utf-8').read())
