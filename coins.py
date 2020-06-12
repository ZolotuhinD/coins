from flask import Flask, request, jsonify, redirect, url_for, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import TIMESTAMP, VARCHAR, SmallInteger, Text, BINARY, CHAR
from sqlalchemy.dialects.mysql import TINYINT, INTEGER, BOOLEAN
from sqlalchemy.schema import Table, MetaData
from os import getenv
from dotenv import load_dotenv
import pymysql
from time import time, strftime, localtime, strptime, mktime
from datetime import datetime


tbl_title = {'Ecount': 'Энергомер'}
skip_names = ('')
exch_names = {'dt': ('Дата', 'Дата показаний'), 't1': ('День', 'Показания t1'), 't2': ('Ночь', 'Показания t2'),
               'id_emetr': ('Счетчик', 'Прибор'), 'id': ('id', 'Номер в системе'), 'emetr': ('Место', 'Место установки энергомера'),
               }
date_names = ('dt')


def ts2str(ts, fmt="%d-%m-%y %H:%M:%S"):
   dt = datetime.fromtimestamp(ts)
   return dt.strftime(fmt)
def str2ts(string, fmt="%d-%m-%y %H:%M:%S"):
   dt = datetime.strptime(string, fmt)
   t_tuple = dt.timetuple()
   return int(mktime(t_tuple))
def get_date_str_short(dt):
   if dt == None:
      return 'None'
   return strftime("%d-%b-%y %H:%M", localtime(dt))
def get_table_id(tbl):
   nm = str(tbl)[str(tbl).find('sb.') + 3:-2]
   table = db.session.query(Table).filter_by(nm=nm).first()
   if table == None:
      table = Table(nm=nm)
      db.session.add(table)
      db.session.commit()
   return table.id

def fill_headers(Table):
   hdrs = []
   for name in dir(Table):
      if (name in skip_names) or ('__' in name) or (name[:1] == '_'):
         continue
      if name in exch_names:
         hdrs.append((exch_names[name][0], exch_names[name][1]))
   return hdrs



def fill_row(record, tbl):
   l=[]
   for name in dir(record):
      if (name in skip_names) or ('__' in name) or (name[:1] == '_'):
         continue
      value = getattr(record, name)
      if name == 'id':
         l.append((value, 'Детализация', url_for('edits', tbl=tbl, id=record.id)))
         continue
      if name in exch_names:
         if name in date_names:
            dt_str = get_date_str_short(value)
            l.append((dt_str[:9], dt_str))
            continue
         else:
            l.append((value, ''))
   return l

def get_table(tbl):
   Table=eval(tbl)
   try:
      records = db.session.query(Table).all()
   except:
      records = False
   table=[]
   bts={}
   res={}
   i=0
   if records:
      for d in records:
         if not i:
            res['idx'] = fill_headers(Table)
         i+=1
         table.append(fill_row(d,tbl))
         res['t'] = table
   else:
      res['t'] =False
   res['new'] = url_for('news', tbl=tbl)
   return res
def get_tbl_title(tbl):
   if tbl in tbl_title:
      title = tbl_title[tbl]
   else:
      title = tbl
   return title
def fill_atr_table(ed):
# Заполняет данные с типами полей для отображения html
   f = {}


   for x in dir(ed):
      if not '__' in x:
         l = {}
         val = getattr(ed, x)
         ty = str(type(val)).split('\'')[1]
         if x in exch_names:
            l['title'] = exch_names[x][0]
         else:
            if ty != 'int' and ty != 'str':
               continue
            l['title'] = x
         l['val'] = val
         l['type'] = ty
         f[x] = l
   return f


load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = getenv("SQLALCHEMY_TRACK_MODIFICATIONS")
app.config['UPLOAD_FOLDER'] = getenv("UPLOAD_FOLDER")
app.config['JSON_AS_ASCII'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SECRET_KEY'] = getenv("SECRET_KEY")
db = SQLAlchemy(app)
engine = db.get_engine()
meta = MetaData(bind=engine)

class Ecount(db.Model):
#   __table__ = Table('ecount', meta, autoload=True)
   __tablename__ = 'ecount'
   id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
   dt = db.Column(db.Integer)
   t1 = db.Column(db.Integer)
   t2 = db.Column(db.Integer)
   id_emetr = db.Column(db.SmallInteger, db.ForeignKey('emetr.id'))
   emetr = relationship('Emetr', foreign_keys=[id_emetr])
   def __repr__(self):
      return "<{} {} {} {}>".format(self.id, ts2str(self.dt), self.t1, self.t2, self.emetr.nm)
class Emetr(db.Model):
#   __table__ = Table('emetr', meta, autoload=True)
   __tablename__ = 'emetr'
   id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
   nm = db.Column(db.String(24))
   mount = db.Column(db.Integer)
   type = db.Column(db.CHAR)
   maxA = db.Column(db.SmallInteger)
   line = db.Column(db.String(48))
   model = db.Column(db.String(32))
   def __repr__(self):
      return "<{}>".format(self.nm)

@app.route('/', methods=['GET', 'POST'])
def index():
   return redirect('/show/Ecount')

@app.route('/show/<t>/')
def show_table(t):
   d={}
   tbl = t[0].upper()+t[1:]
   d = get_table(tbl)
   d['title'] = get_tbl_title(tbl)
   d['tbl'] = tbl
   return render_template("brows.html", d=d)

@app.route('/s/<tbl>/<int:id>/edit/', methods=['GET', 'POST'])
def edits(tbl, id):
   ed = db.session.query(eval(tbl)).filter_by(id=id).one()
   f = fill_atr_table(ed)
   if request.method == 'POST':
      for d in request.form:
         if d in f:
            exec("ed.%s = request.form['%s']" % (d, d))
      db.session.commit()
      return redirect(url_for('show_table', t=tbl))
   else:
      d = {}
      d['rec'] = f
      d['title'] = get_tbl_title(tbl)
      d['tbl'] = tbl
      return render_template('edits.html', d=d)
   return

@app.route('/detail/<tbl>/<int:id>/', methods=['GET', 'POST'])
def detail(tbl, id):
   update_access_list()
   ed = db.session.query(eval(tbl)).filter_by(id=id).one()
   f = fill_atr_table(ed)
   d = {}
   d['rec'] = f
   d['title'] = get_tbl_title(tbl)
   d['tbl'] = tbl
   return render_template('detail.html', d=d)

@app.route('/news/<tbl>', methods=['GET', 'POST'])
def news(tbl):
   if hasattr(eval(tbl),'dt'):
      nr = eval(tbl)(dt=int(mktime(datetime.now().timetuple())))
   else:
      nr = eval(tbl)()
   db.session.add(nr)
   db.session.commit()
   return redirect(url_for('show_table', t=tbl))

if __name__ == '__main__':
   app.run()
