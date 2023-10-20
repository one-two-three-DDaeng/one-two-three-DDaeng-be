from flask import Flask, request, render_template

from db_conn_sqlalchemy import dbSqlAlchemy
from sqlalchemy.sql import text
import pandas as pd
from flask_restx import Api, Resource, fields
from difflib import SequenceMatcher
import json

#문장 유사도 확인
def similar(a, b):
    return round(SequenceMatcher(None, a, b).ratio(),3)

app = Flask(__name__)

api = Api(app, version='1.0', title='API 문서', description='DDAENG_API 문서', doc="/")

api = api.namespace('api',description='Movie API')
# api_line = api.namespace('movie',description='line_content API')

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
        session.commit()

        linetotal = int(total.loc[0][0])

        context = {'count':linetotal}
        response.append(context)
        # context = json.dumps(context, ensure_ascii=False)
    
        return response


@api.route('/movie/line/<int:num>')
class MovieContent(Resource):
    def get(self, num):
        response = []
        res = str(num)

        engine,session = dbSqlAlchemy.get_engine()
        querytext = text(f"select * from movie_line_mng where line_seq = {res} and use_yn = 'y'") #
        lineinfo = pd.read_sql_query(querytext, engine)
        session.commit()

        if lineinfo.empty:
            return response
        else:
            context = dict(lineinfo.loc[0])
            context['line_seq'] = int(context['line_seq'])
            context['line'] = context['line'].replace(' ','√')
            del context['use_yn']

            response.append(context)
            # context = json.dumps(context, ensure_ascii=False).replace('\"',"")
            
        return response

@api.route('/movie/line/insert')
class MovieLineCURD(Resource):

    @api.expect(movie_model)
    def post(self):
        response = []
        movie_name = str(request.json.get('movie_name'))
        line = str(request.json.get('line'))

        engine,session = dbSqlAlchemy.get_engine()
        conn = engine.raw_connection()
        cursor = conn.cursor()

        querytext = text("select line_seq from movie_line_mng order by line_seq desc limit 1;") #
        lastnum = int(pd.read_sql_query(querytext, engine).loc[0][0])
        line_seq = str(lastnum+1)
        session.commit()

        #중복 체크
        similar_score = 0.0
        similar_std = 0.5
        querytext = text("select movie_name,line from movie_line_mng;") #
        movieinfo = pd.read_sql_query(querytext, engine)

        namelist = movieinfo[movieinfo['movie_name'] == movie_name]

        # 같은 이름의 영화제목이 있을 경우 -> 유사도 검사
        if not namelist.empty:
            linelist = list(namelist[['line']].iloc[:,0])

            for li in linelist:
                similar_score = similar(line,li)

                if similar_score >= similar_std:
                    response = [{'result':False, 'reason':f'similar line exist {similar_score}'}]
                    return response

        # 새로운 영화제목 또는 유사도가 유사도 기준 이하일 경우 DB저장
        if namelist.empty or similar_score < similar_std:
            try:
                query = f"""insert into movie_line_mng(line_seq, movie_name, line, use_yn)
                        values('{line_seq}','{movie_name}','{line}','{"y"}');"""
                cursor.execute(query)
                conn.commit()

                response = [{'result':True}]

            except:
                response = [{'result':False, 'reason':'server err'}]

            return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)