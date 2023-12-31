from flask import Flask, request, render_template

from db_conn_sqlalchemy import dbSqlAlchemy
from sqlalchemy.sql import text
import pandas as pd
from flask_restx import Api, Resource, fields
from difflib import SequenceMatcher
import json
import re

#문장 유사도 확인 함수
def similar(a, b):
    return round(SequenceMatcher(None, a, b).ratio(),3)


app = Flask(__name__)

api = Api(app, version='1.0', title='API 문서', description='DDAENG_API 문서', doc="/")
api = api.namespace('api',description='Movie API')

movie_model = api.model('movie_model', {
    'movie_name':fields.String(description="영화 제목", requested=True),
    'line':fields.String(description="영화 명대사", requested=True),
})

@api.route('/movie/line/count')
class MovieCount(Resource):
    def get(self):
        response = []

        engine,session = dbSqlAlchemy.get_engine()
        querytext = text("select count(*) from movie_line_mng;") #
        total = pd.read_sql_query(querytext, engine)

        querytext = text("select line_seq from movie_line_mng order by line_seq desc limit 1;") #
        db_seq = int(pd.read_sql_query(querytext, engine).loc[0][0])

        session.commit()

        linetotal = int(total.loc[0][0])

        response = [{'count':linetotal,'last_seq':db_seq}]
        context = {'data':response}
    
        return context

@api.route('/movie/line')
class MoviePost(Resource):
    @api.expect(movie_model)
    def post(self):
        response = []
        movie_name = str(request.json.get('movie_name'))
        txt = str(request.json.get('line'))

        #line 전처리 : 앞 뒤 띄어쓰기 제거
        line = txt.strip()

        #line 전처리 : 특수 문자 처리
        repeat_re = re.compile('[\,|\.|?|!^\s]{2,}')
        remove_re = re.compile('[-=+#/:^@*\"※~ㆍ』‘|\(\)\[\]`\'…》\”\“\’·]')
        
        line = re.sub(remove_re,'',line)

        repeat_txt = repeat_re.findall(line)
        if repeat_txt != []:
            for k in repeat_txt:
                line = line.replace(k,k[0])

        engine,session = dbSqlAlchemy.get_engine()
        conn = engine.raw_connection()
        cursor = conn.cursor()

        querytext = text("select line_seq from movie_line_mng order by line_seq desc limit 1;") #
        lastnum = int(pd.read_sql_query(querytext, engine).loc[0][0])
        line_seq = str(lastnum+1)

        #중복 체크
        similar_score = 0.0
        similar_std = 0.5
        search_word = [movie_name[0] +"%", "%"+movie_name[-1]]
        querytext = text(f"""select movie_name,line from movie_line_mng 
                         where movie_name like '{search_word[0]}' or movie_name like '{search_word[1]}';""") #
        movieinfo = pd.read_sql_query(querytext, engine)

        namelist = movieinfo
        session.commit()

        # 같은 이름의 영화제목이 있을 경우 -> 유사도 검사
        if not namelist.empty:
            linelist = list(namelist[['line']].iloc[:,0])

            for li in linelist:
                similar_score = similar(line,li)

                if similar_score >= similar_std:
                    response = [{'result':False, 'err_reason':f'similar line exist {similar_score}'}]
                    context = {'data':response}
                    return context

        # 새로운 영화제목 또는 유사도가 유사도 기준 이하일 경우 DB저장
        if namelist.empty or similar_score < similar_std:
            try:
                query = f"""insert into movie_line_mng(line_seq, movie_name, line, use_yn)
                        values('{line_seq}','{movie_name}','{line}','{"y"}');"""
                cursor.execute(query)
                conn.commit()

                response = [{'result':True}]

            except:
                response = [{'result':False, 'err_reason':'server err'}]

            context = {'data':response}
            return context

@api.route('/movie/line/<int:num>')
class MovieSimple(Resource):
    def get(self, num):
        response = []
        line_seq = str(num)

        engine,session = dbSqlAlchemy.get_engine()
        querytext = text(f"select * from movie_line_mng where line_seq = {line_seq} and use_yn = 'y'") #
        lineinfo = pd.read_sql_query(querytext, engine)
        session.commit()

        if lineinfo.empty:
            context = {'data':response}
            return context
        
        else:
            context = dict(lineinfo.loc[0])
            context['line_seq'] = int(context['line_seq'])
            context['line'] = context['line'].replace(' ','√')
            del context['use_yn']

            response.append(context)
            # context = json.dumps(context, ensure_ascii=False).replace('\"',"")
            
        context = {'data':response}
        return context

    def delete(self, num):
        response = []
        line_seq = str(num)
        
        try:
            engine,session = dbSqlAlchemy.get_engine()
            conn = engine.raw_connection()
            cursor = conn.cursor()

            querytext = text("select line_seq from movie_line_mng order by line_seq desc limit 1;") #
            db_seq = int(pd.read_sql_query(querytext, engine).loc[0][0])

            if int(line_seq) == int(db_seq):
                query = f"""delete from movie_line_mng where line_seq = {line_seq};"""
                cursor.execute(query)
                
                session.commit()
                conn.commit()

                response = [{'result':True}]

            else:
                response = [{'result':False,'err_reason':'it is not last num of DB. this api can delete only last data'}]
        except:
            response = [{'result':False, 'err_reason':'server err'}]


        context = {'data':response}
        return context



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)