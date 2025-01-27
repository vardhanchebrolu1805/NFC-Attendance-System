from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime
from sqlalchemy import text
from flask.cli import with_appcontext


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    serial_id = db.Column(db.String(20), unique=True, nullable=False)
    attendance_records = db.relationship('Attendance', backref='student', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'serial_id': self.serial_id}


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today())
    time = db.Column(db.Time, nullable=False, default=datetime.datetime.now().time())
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'date': self.date.isoformat(), 'time': self.time.isoformat(), 'student_id': self.student_id}


@app.cli.command()
@with_appcontext
def create_tables():
    db.create_all()

    # Add the time column to the attendance table, if it does not already exist
    db.session.execute(text('ALTER TABLE attendance ADD COLUMN IF NOT EXISTS time TIME NOT NULL DEFAULT "00:00:00"'))
    db.session.commit()

    # Update the existing attendance records with the current time
    attendance_records = Attendance.query.all()
    for record in attendance_records:
        db.session.execute(text(f'UPDATE attendance SET time = "{datetime.datetime.now().time().strftime("%H:%M:%S")}" WHERE id = {record.id}'))
    db.session.commit()


@app.teardown_appcontext
def close_db(error):
    db.session.close()


@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'GET':
        students = Student.query.all()
        return jsonify([student.to_dict() for student in students])
    elif request.method == 'POST':
        if not request.json or not 'serial_id' in request.json:
            return jsonify({'error': 'Serial ID is required'}), 400

        student = Student.query.filter_by(serial_id=request.json['serial_id']).first()
        if not student:
            return jsonify({'error': 'Invalid Serial ID'}), 400

        attendance_record = Attendance(student_id=student.id)
        db.session.add(attendance_record)
        db.session.commit()

        return jsonify({'success': 'Attendance recorded successfully'}), 201
    else:
        return jsonify({'error': 'This endpoint only supports GET and POST requests'}), 405


@app.route('/attendance/<int:student_id>', methods=['GET'])
def get_attendance(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    attendance_records = Attendance.query.filter_by(student_id=student.id).all()
    if not attendance_records:
        return jsonify({'error': 'No attendance records found'}), 404

    return jsonify([record.to_dict() for record in attendance_records])


if __name__ == '__main__':
    app.run(debug=True)
