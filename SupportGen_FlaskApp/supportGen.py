from flask import Flask, jsonify, request
import os
import pymysql
from pymysql import Error
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

app = Flask(__name__)

# def get_db_connection():
#     connection = pymysql.connect(
#         user=os.environ['DB_USER'],
#         password=os.environ['DB_PASS'],
#         database=os.environ['DB_NAME'],
#         unix_socket=f"/cloudsql/{os.environ['CLOUD_SQL_CONNECTION_NAME']}"
#     )
#     return connection


# Connecting to the database - (local database)
def get_db_connection():
    """Creates and returns a MySQL connection"""
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None
    
@app.route('/')
def home():
    response = "Welcome to Support Gen!"

    return response

#========================================= USER API =======================================================

# API to get all the users
@app.route('/users', methods=['GET'])
def get_users():
   
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT * FROM users
    """

    cursor.execute(query)
    results = cursor.fetchall()
    # cursor.close()
    connection.close()
    return jsonify(results), 200

#========================================= TICKETS API =======================================================

# API to get all the tickets
@app.route('/tickets', methods=['GET'])
def get_tickets():
   
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT * FROM tickets
    """

    cursor.execute(query)
    results = cursor.fetchall()
    # cursor.close()
    connection.close()
    return jsonify(results), 200

#*********************************************************************************************

# API to create a new ticket
@app.route('/tickets', methods=['POST'])
def create_ticket():
    data = request.get_json()

     # Debug: Print the received data
    print(f"Received JSON data: {data}")

    user = data.get('user_id')
    issue = data.get('issue_type_id')
    status = data.get('status', 'open')  # Default status is 'open'
    priority = data.get('priority')

    connection = get_db_connection()
    cursor = connection.cursor()

    # Validate foreign key relationships (e.g., User_ID must exist)
    cursor.execute("SELECT COUNT(*) FROM Users WHERE User_ID = %s", (user,))
    if cursor.fetchone()[0] == 0:
        return jsonify({'error': f'User ID {user} does not exist'}), 404
    
    cursor.execute("SELECT COUNT(*) FROM Issue_Types WHERE Issue_Type_ID = %s", (issue,))
    if cursor.fetchone()[0] == 0:
        return jsonify({'error': f'Issue Type ID {issue} does not exist'}), 404
    

    # Generating the chat_id (need to pass the ticket description here)
    chat_query = "INSERT INTO Chats (Transcript) VALUES (%s)"
    transcript = "Chat initiated for ticket"
    cursor.execute(chat_query, (transcript,))
    connection.commit()

    chat = cursor.lastrowid

    # Insert new ticket
    query = """
        INSERT INTO tickets (User_ID, Issue_Type_ID, Chat_ID, Status, Priority)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user, issue, chat, status, priority))
    connection.commit()

    ticket_id = cursor.lastrowid  # Get the ID of the newly inserted ticket
    connection.close()

    return jsonify({'message': 'Ticket created successfully', 'ticket_id': ticket_id, 'chat_id': chat}), 201

#***************************************************************************************
# API to update a ticket by Ticket_ID

@app.route('/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    data = request.get_json()

    # Debug: Print received data
    print(f"Received update data: {data}")

    # Validate input
    if not data or 'priority' not in data:
        return jsonify({'error': 'Missing priority field in request data'}), 400

    # Extract the new priority
    priority = data.get('priority')

    # Check if priority is valid
    if not priority:
        return jsonify({'error': 'Invalid or empty priority value provided'}), 400

    # Generate SQL query to update the priority
    update_query = "UPDATE tickets SET Priority = %s WHERE Ticket_ID = %s"

    # Execute the query
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Failed to connect to the database'}), 500

    cursor = connection.cursor()
    try:
        cursor.execute(update_query, (priority, ticket_id))
        connection.commit()

        # Check if the ticket was updated
        if cursor.rowcount == 0:
            return jsonify({'error': f'Ticket with ID {ticket_id} not found'}), 404

        return jsonify({'message': f'Ticket ID {ticket_id} priority updated to {priority} successfully'}), 200
    except pymysql.MySQLError as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

#********************************************************************
# API to delete a ticket by Ticket_ID

@app.route('/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    """Delete a ticket by its ID."""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor()

    # Check if the ticket exists
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE Ticket_ID = %s", (ticket_id,))
    if cursor.fetchone()[0] == 0:
        connection.close()
        return jsonify({'error': f'Ticket with ID {ticket_id} does not exist'}), 404

    # Delete the ticket
    try:
        cursor.execute("DELETE FROM tickets WHERE Ticket_ID = %s", (ticket_id,))
        connection.commit()
        connection.close()
        return jsonify({'message': f'Ticket with ID {ticket_id} deleted successfully'}), 200
    except pymysql.MySQLError as e:
        connection.rollback()
        connection.close()
        return jsonify({'error': str(e)}), 500


#=========================================== DEPARTMENTS API ===============================================
@app.route('/dept', methods=['GET'])
def get_departments():
   
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT * FROM departments
    """

    cursor.execute(query)
    results = cursor.fetchall()
    # cursor.close()
    connection.close()
    return jsonify(results), 200


# API to get 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
