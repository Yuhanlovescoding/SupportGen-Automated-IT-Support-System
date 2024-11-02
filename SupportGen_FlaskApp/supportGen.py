from flask import Flask, jsonify
import os
import pymysql

app = Flask(__name__)

def get_db_connection():
    connection = pymysql.connect(
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=os.environ['DB_NAME'],
        unix_socket=f"/cloudsql/{os.environ['CLOUD_SQL_CONNECTION_NAME']}"
    )
    return connection

@app.route('/')
def get_user_tickets():
    connection = get_db_connection()
    cursor = connection.cursor()
    
    
    query = """
        SELECT Ticket_ID
        FROM Ticket
        WHERE User_ID = %s
    """
    cursor.execute(query, (1,))
    results = cursor.fetchall()
    
    connection.close()
    
   
    if results:
        ticket_ids = ', '.join([str(row[0]) for row in results])
        response = (
            "Querying tickets submitted by the employee with "
            f"User ID: 1\n: Submitted ticket IDs: {ticket_ids}"
        )
    else:
        response = "No tickets found for User ID: 1."
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
