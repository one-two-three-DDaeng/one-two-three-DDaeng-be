from flask import Flask, request, render_template

from db_conn_sqlalchemy import dbSqlAlchemy
from sqlalchemy.sql import text
import pandas as pd
from flask_restx import Api, Resource, fields
import json

app = Flask(__name__)

api = Api(app, version='1.0', title='API 문서', description='DDAENG_API 문서', doc="/")

api = api.namespace('movie',description='Movie API')
# api_line = api.namespace('movie',description='line_content API')

movie_model = api.model('movie_model', {
    'num':fields.Integer(description="0 이상의 정수", required=True)
})

@api.route('/line/count')
class MovieCount(Resource):
    def get(self):
        engine,session = dbSqlAlchemy.get_engine()
        querytext = text("select count(*) from movie_line_mng;") #
        total = pd.read_sql_query(querytext, engine)
        session.commit()

        linetotal = int(total.loc[0][0])

        context = {'count':linetotal}
        context = json.dumps(context, ensure_ascii=False).replace('\"',"")
    
        return context


@api.route('/line/content/<int:num>')
class MovieContent(Resource):
    def get(self, num):
        res = str(num)

        engine,session = dbSqlAlchemy.get_engine()
        querytext = text(f"select * from movie_line_mng where line_seq = {res};") #
        lineinfo = pd.read_sql_query(querytext, engine)
        session.commit()

        if lineinfo.empty:
            context = "None"
        else:
            context = dict(lineinfo.loc[0])
            context['line_seq'] = str(context['line_seq'])
            context = json.dumps(context, ensure_ascii=False).replace('\"',"")
            
        return context

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)