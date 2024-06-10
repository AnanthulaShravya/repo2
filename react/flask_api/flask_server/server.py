from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mysqldb import MySQL
import json
import datetime
from dotenv import load_dotenv
import os
import logging


#loading environment variables i.e .env file
load_dotenv()


#initializing Flask app
app = Flask(__name__)


#enable CORS (cross origin resurce sharing)
CORS(app)


#configure logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)



#configure MySQL connection using environment variable i.e connecting it to .env file variables
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')



#Initailoizing MYSQL connection i.e backened mysql 
mysql = MySQL(app)



# Class to handle centralized error handling
class CentralizedErrorHandler:
    @staticmethod
    def handle_error(error, message=""):
        return jsonify({'error': str(error), 'message': message}), 500
    

    
# Function to execute SQL query with parameters
def execute_query(query, params=None):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(query, params)
        mysql.connection.commit()
    except Exception as e:
        raise e
    finally:
        cursor.close()


# Function to fetch results from SQL query with parameters
def fetch_results(query, params=None):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()
        return_list = []
        for row in results:
            result_dict = {}
            for i, column in enumerate(columns):
                result_dict[column] = row[i]
            return_list.append(result_dict)
        return return_list
    except Exception as e:
        raise e
    finally:
        cursor.close()


# Route to retrieve all patients
@app.route("/patient", methods=['GET'])
def patients():
    try:
        start_time=datetime.datetime.now()    # start time of request processing
        query = "SELECT * FROM patient"
        patients = fetch_results(query)
        response_time=datetime.datetime.now()-start_time   # claculate time taken for request processing
        logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")    # log request , response status and time taken
        return json.dumps(patients)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to retrieve patient details")
    


# Route to retrieve patient reports by patient_Id
@app.route("/patient/<string:patient_id>/reports", methods=['GET'])
def patient_reports(patient_id):
    try:
        start_time=datetime.datetime.now()
        query = "SELECT * FROM patient_reports WHERE patient_id=%s"
        results = fetch_results(query, (patient_id,))
        
        for report in results:
            for key, value in report.items():
                if isinstance(value, datetime.date):
                    report[key] = value.strftime('%Y-%m-%d')
        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.url}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        return json.dumps(results)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to retrieve patient reports")
    



# Route to retrieve all doctors
@app.route("/doctor/", methods=['GET'])
def doctors():
    try:
        start_time=datetime.datetime.now()
        query = "SELECT * FROM doctor"
        doctors = fetch_results(query)
        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.url}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        return json.dumps(doctors)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to retrieve doctor details")
    



# Route to handle doctor attendance
@app.route("/doctor/<string:doctor_id>/attendance", methods=['GET', 'PUT'])
def doctor_attendance(doctor_id):
    try:
        start_time=datetime.datetime.now()


        if request.method == 'GET':    # Retrieve doctor attendance
            query = "SELECT * FROM doctor_attendance WHERE doctor_id=%s"
            attendance = fetch_results(query, (doctor_id,))
            response_time=datetime.datetime.now()-start_time
            logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
            return jsonify(attendance)
        

        elif request.method == 'PUT':   # Update doctor attendance
            data = request.get_json()
            attendance = data['attendance']
            
            for entry in attendance:
                date = entry['attendance_date']
                status = entry['status']
                query = "SELECT * FROM doctor_attendance WHERE doctor_id=%s AND attendance_date=%s"
                existing_entry = fetch_results(query, (doctor_id, date))
                
                if existing_entry:
                    query = "UPDATE doctor_attendance SET status=%s WHERE doctor_id=%s AND attendance_date=%s"
                    execute_query(query, (status, doctor_id, date))
                else:
                    query = "INSERT INTO doctor_attendance (doctor_id, attendance_date, status) VALUES (%s, %s, %s)"
                    execute_query(query, (doctor_id, date, status))

            response_time=datetime.datetime.now()-start_time
            logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
            return jsonify({"message": "Attendance updated successfully"})
        
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to update attendance")
    


# Route to retrieve patients of a doctor
@app.route("/doctor/<string:doctor_id>/patients", methods=['GET'])
def doctor_patients(doctor_id):
    try:
        start_time=datetime.datetime.now()
        query = """
            SELECT p.id, p.name, p.age, p.gender, p.email
            FROM doctor_patients dp
            JOIN patient p ON dp.patient_id = p.id
            WHERE dp.doctor_id = %s
        """
        patient_details = fetch_results(query, (doctor_id,))
        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        return jsonify(patient_details)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to retrieve patient details")
    


#Route to retrieve appointments by user_id i.e either patient or doctor 
@app.route("/appointments/<string:user_id>", methods=['GET'])
def appointments(user_id):
    try:
        start_time=datetime.datetime.now()
        query = """
            SELECT 
                a.id,
                a.appointment_date,
                a.appointment_time,
                a.status,
                p.name AS patient_name,
                d.name AS doctor_name
            FROM appointments a
            JOIN patient p ON a.patient_id = p.id
            JOIN doctor d ON a.doctor_id = d.id
            WHERE a.patient_id=%s OR a.doctor_id=%s
        """
        results = fetch_results(query, (user_id, user_id))
        
        for appointment in results:
            for key, value in appointment.items():
                if isinstance(value, datetime.date):
                    appointment[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, datetime.time):
                    appointment[key] = value.strftime('%H:%M:%S')
                elif isinstance(value, datetime.timedelta):
                    appointment[key] = str(value)
        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        
        return json.dumps(results)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")  
        return CentralizedErrorHandler.handle_error(e, "Failed to fetch appointments")
    


#Route to add new appointment
@app.route("/appointments", methods=['PUT'])
def update_appointments():
    try:
        start_time=datetime.datetime.now()
        data = request.get_json()
        appointments = data['appointmentData']
        
        for entry in appointments:

            # Validate appointment date
            if not isinstance(entry['date'], str):
                raise ValueError("Appointment date must be a string")
        
            # Validate appointment time
            if not isinstance(entry['time'], str):
                raise ValueError("Appointment time must be a string")
            
            # Validate patient ID
            if not isinstance(entry['patientId'], str):
                raise ValueError("Patient ID must be an integer")
            
            # Validate doctor ID
            if not isinstance(entry['doctorId'], str):
                raise ValueError("Doctor ID must be an integer")
            
            # Validate status
            if not isinstance(entry['status'], str):
                raise ValueError("Status must be a string")
            if entry['status'] not in ['pending', 'confirmed', 'cancelled']:
                raise ValueError("Status must be one of: pending, confirmed, cancelled")
            
            query = """
                INSERT INTO appointments (appointment_date, appointment_time, patient_id, doctor_id, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute_query(query, (entry['date'], entry['time'], entry['patientId'], entry['doctorId'], entry['status']))

        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        return jsonify({"message": "Appointments updated successfully"})
    
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}") 
        return CentralizedErrorHandler.handle_error(e, "Failed to update appointments")




# Route to update appointment status
@app.route("/appointments/<int:id>", methods=['PATCH'])
def update_status(id):
    try:
        start_time=datetime.datetime.now()
        data = request.get_json()
        status = data.get('status')
        
        query = "UPDATE appointments SET status=%s WHERE id=%s"
        execute_query(query, (status, id))
        response_time=datetime.datetime.now()-start_time
        logger.info(f"Request:{request.method} {request.path}, Response Status:200, Time taken: {response_time.total_seconds()} seconds")
        return jsonify({"message": "Status updated successfully"})
    
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return CentralizedErrorHandler.handle_error(e, "Failed to update status")
    


if __name__ == "__main__":
    app.run(debug=True)

