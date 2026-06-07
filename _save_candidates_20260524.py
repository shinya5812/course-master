# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.argv = ['result_checker.py', '--save',
    '{"date":"2026-05-24","venue":"新潟","candidates":['
    '[5,1,"ウインブリザード","条件C",24.1],'
    '[5,3,"ゼータレティクル","条件C",21.4],'
    '[5,6,"マイネルアルゴー","条件C",46.8],'
    '[5,9,"ジージージェット","条件C",26.2]'
    ']}']
exec(open('result_checker.py', encoding='utf-8').read())
