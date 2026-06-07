# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')

# 新潟10R（尖閣湾特別）1着: 馬番9 マイネルアズーロ 4.1倍
sys.argv = ['result_checker.py', '--results',
    '{"10":[9,"マイネルアズーロ",4.1]}']
exec(open('result_checker.py', encoding='utf-8').read())
