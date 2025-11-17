from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import os, io, uuid, datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import qrcode

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL','sqlite:///db.sqlite')
app.config['BASE_URL'] = os.environ.get('BASE_URL','http://localhost:5000')
db = SQLAlchemy(app)

class Patient(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    phone=db.Column(db.String)
    email=db.Column(db.String)
    created_at=db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Order(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    order_no=db.Column(db.String, unique=True)
    patient_id=db.Column(db.Integer, db.ForeignKey('patient.id'))
    patient=db.relationship('Patient')
    pdf_path=db.Column(db.String)
    token=db.Column(db.String, unique=True)
    created_at=db.Column(db.DateTime, default=datetime.datetime.utcnow)

class TestResult(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    order_id=db.Column(db.Integer, db.ForeignKey('order.id'))
    test_name=db.Column(db.String)
    result=db.Column(db.String)
    ref_range=db.Column(db.String)

@app.before_first_request
def init_db():
    db.create_all()

ADMIN_USER=os.environ.get('ADMIN_USER','NAGENDRA')
ADMIN_PASS=os.environ.get('ADMIN_PASS','6383456268')

@app.route('/api/login', methods=['POST'])
def login():
    data=request.json
    if data.get('username')==ADMIN_USER and data.get('password')==ADMIN_PASS:
        return jsonify({'ok':True})
    return jsonify({'ok':False}),401

@app.route('/api/patient', methods=['POST'])
def create_patient():
    data=request.json
    p=Patient(name=data.get('name'), phone=data.get('phone'), email=data.get('email'))
    db.session.add(p); db.session.commit()
    return jsonify({'id':p.id})

@app.route('/api/order', methods=['POST'])
def create_order():
    data=request.json
    order_no=f"SURYA-{int(datetime.datetime.utcnow().timestamp())}"
    o=Order(order_no=order_no, patient_id=data['patient_id'])
    db.session.add(o); db.session.commit()
    return jsonify({'order_id':o.id,'order_no':order_no})

@app.route('/api/order/<int:oid>/tests', methods=['POST'])
def add_tests(oid):
    items=request.json
    for t in items:
        x=TestResult(order_id=oid, test_name=t['test_name'], result=t['result'], ref_range=t.get('ref_range'))
        db.session.add(x)
    db.session.commit()
    return jsonify({'ok':True})

def generate_pdf(order):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf)
    styles=getSampleStyleSheet()
    story=[Paragraph(f"SURYA DIAGNOSTICS REPORT: {order.order_no}", styles['Title']), Spacer(1,8)]
    story.append(Paragraph(f"Patient: {order.patient.name}", styles['Normal']))
    story.append(Spacer(1,8))

    tests=TestResult.query.filter_by(order_id=order.id).all()
    data=[['Test','Result','Range']]
    for t in tests:
        data.append([t.test_name, t.result, t.ref_range])
    table=Table(data)
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black)]))
    story.append(table)

    token=order.token or str(uuid.uuid4())
    order.token=token
    db.session.commit()

    qr=qrcode.make(f"{app.config['BASE_URL']}/r/{token}")
    qbuf=io.BytesIO(); qr.save(qbuf,format='PNG'); qbuf.seek(0)
    story.append(Image(qbuf, width=100, height=100))

    doc.build(story)
    buf.seek(0)
    return buf.read()

@app.route('/api/order/<int:oid>/generate', methods=['POST'])
def gen(oid):
    o=Order.query.get(oid)
    pdf=generate_pdf(o)
    os.makedirs("storage", exist_ok=True)
    path=f"storage/{o.order_no}.pdf"
    with open(path,'wb') as f: f.write(pdf)
    o.pdf_path=path; db.session.commit()
    return jsonify({'pdf_path':path,'public_link':f"/r/{o.token}"})

@app.route('/r/<token>')
def pub(token):
    o=Order.query.filter_by(token=token).first()
    if not o: return "Not found",404
    return send_file(o.pdf_path, as_attachment=False)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)
                     
