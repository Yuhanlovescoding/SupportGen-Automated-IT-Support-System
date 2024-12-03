from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import pymysql
from pymysql import Error
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

def get_db_connection():
    connection = pymysql.connect(
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASS'),
    database=os.environ.get('DB_NAME'),
    unix_socket=f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME')}",
    cursorclass=pymysql.cursors.DictCursor 
)
    return connection

# ============================ Home =================================
@app.route('/')
def home():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch ticket counts
    query_counts = {
        "open": "SELECT COUNT(*) AS count FROM `Ticket` WHERE `Status` = 'Open'",
        "resolved": "SELECT COUNT(*) AS count FROM `Ticket` WHERE `Status` = 'Resolved'",
        "in_progress": "SELECT COUNT(*) AS count FROM `Ticket` WHERE `Status` = 'In Progress'"
    }
    counts = {}
    for key, query in query_counts.items():
        cursor.execute(query)
        counts[key] = cursor.fetchone()["count"]

    

    query_tickets = """
    SELECT 
        Ticket.*,
        IssueType.Issue_Description AS IssueType_Description,
        Keyword.Keyword_Text AS Keyword_Text
    FROM 
        Ticket
    LEFT JOIN 
        IssueType ON Ticket.Issue_type_ID = IssueType.Issue_Type_ID
    LEFT JOIN 
        Keyword ON Ticket.Keyword_ID = Keyword.Keyword_ID
    ORDER BY 
        Ticket.Date_created DESC
    """
    cursor.execute(query_tickets)
    recent_tickets = cursor.fetchall()

    connection.close()
    
    return render_template(
        'home.html',
        title="Home",
        open_tickets=counts["open"],
        resolved_tickets=counts["resolved"],
        in_progress_tickets=counts["in_progress"],
        recent_tickets=recent_tickets,
    )

#========================================= USER API =======================================================

# API to get all the users
@app.route('/users', methods=['GET'])
def get_users():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = "SELECT * FROM User"
        cursor.execute(query)
        results = cursor.fetchall()
        logging.debug(f"Users fetched: {results}")

        connection.close()
        return render_template('users.html', users=results, title="Users"), 200
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return "An error occurred while fetching users.", 500
    
#========================================= TICKET API =======================================================

# API to get tickets   
@app.route('/tickets')
def ticket_list():
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT 
            Ticket.*,
            IssueType.Issue_Description AS IssueType_Description
        FROM 
            Ticket
        LEFT JOIN 
            IssueType ON Ticket.Issue_type_ID = IssueType.Issue_Type_ID
    """
    cursor.execute(query)
    tickets = cursor.fetchall()

    connection.close()
    return render_template('ticket_list.html', tickets=tickets, title="Tickets")

@app.route('/ticket/<int:ticket_id>')
def ticket_details(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    
    query = """
        SELECT 
            Ticket.*,
            IssueType.Issue_Description AS IssueType_Description
        FROM 
            Ticket
        LEFT JOIN 
            IssueType ON Ticket.Issue_type_ID = IssueType.Issue_Type_ID
        WHERE 
            Ticket.Ticket_ID = %s
    """
    cursor.execute(query, (ticket_id,))
    ticket = cursor.fetchone()

    connection.close()

    if not ticket:
        return "Ticket not found", 404
    return render_template('ticket_details.html', ticket=ticket, title=f"Ticket {ticket_id}")

#*********************************************************************************************
# API to search Tickets
@app.route('/search-tickets-keyword', methods=['GET', 'POST'])
def search_tickets_keyword():
    if request.method == 'POST':
        keyword = request.form['keyword'].lower()
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            SELECT Ticket.*, 
                   Keyword.Keyword_Text, 
                   IssueType.Issue_Description AS IssueType_Description
            FROM Ticket
            LEFT JOIN Keyword ON Ticket.Keyword_ID = Keyword.Keyword_ID
            LEFT JOIN IssueType ON Ticket.Issue_type_ID = IssueType.Issue_Type_ID
            WHERE LOWER(Keyword.Keyword_Text) LIKE %s
        """
        cursor.execute(query, (f"%{keyword}%",))
        tickets = cursor.fetchall()
        connection.close()

        return render_template('search_results.html', tickets=tickets, title="Search Results by Keyword")

    return render_template('search_form.html', form_title="Search Tickets by Keyword", field_name="keyword")



@app.route('/search-tickets-issuetype', methods=['GET', 'POST'])
def search_tickets_issuetype():
    if request.method == 'POST':
        issuetype = request.form['issuetype'].lower()
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            SELECT Ticket.*, 
                   Keyword.Keyword_Text, 
                   IssueType.Issue_Description AS IssueType_Description
            FROM Ticket
            LEFT JOIN Keyword ON Ticket.Keyword_ID = Keyword.Keyword_ID
            LEFT JOIN IssueType ON Ticket.Issue_type_ID = IssueType.Issue_Type_ID
            WHERE LOWER(IssueType.Issue_Description) LIKE %s
        """
        cursor.execute(query, (f"%{issuetype}%",))
        tickets = cursor.fetchall()
        connection.close()

        return render_template('search_results.html', tickets=tickets, title="Search Results by IssueType")

    return render_template('search_form.html', form_title="Search Tickets by IssueType", field_name="issuetype")




#*********************************************************************************************
# API to create a new ticket
@app.route('/create-ticket', methods=['GET', 'POST'])
def create_ticket_page():
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        logging.debug(f"Form data received: {request.form}")
        
        user_id = request.form['user_id']
        issue_type_id = request.form['issue_type_id']
        keyword_id = request.form['keyword_id']
        status = request.form['status']
        priority = request.form['priority']
        date_resolved = request.form.get('date_resolved') or None
        is_withdrawn = bool(int(request.form['is_withdrawn']))  # Convert "0"/"1" to boolean

        try:
            # check if User_ID exists
            cursor.execute("SELECT COUNT(*) AS count FROM User WHERE User_ID = %s", (user_id,))
            if cursor.fetchone()['count'] == 0:
                return "User ID does not exist", 404

            # check if Issue_Type_ID exits
            cursor.execute("SELECT COUNT(*) AS count FROM IssueType WHERE Issue_Type_ID = %s", (issue_type_id,))
            if cursor.fetchone()['count'] == 0:
                return "Issue Type ID does not exist", 404

            # check if Keyword_ID exits
            cursor.execute("SELECT COUNT(*) AS count FROM Keyword WHERE Keyword_ID = %s", (keyword_id,))
            if cursor.fetchone()['count'] == 0:
                return "Keyword ID does not exist", 404

            # insert new Tickt data
            ticket_query = """
                INSERT INTO Ticket (User_ID, Issue_type_ID, Keyword_ID, Status, Priority, Date_created, Date_resolved, Is_Withdrawn)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
            """
            cursor.execute(ticket_query, (user_id, issue_type_id, keyword_id, status, priority, date_resolved, is_withdrawn))
            connection.commit()
            new_ticket_id = cursor.lastrowid
            
            logging.info(f"Ticket created successfully with ID: {new_ticket_id}")
            return redirect(url_for('ticket_list'))  # redirect to the Ticket list page

        except Exception as e:
            logging.error(f"Error creating ticket: {e}")
            return "An error occurred while creating the ticket.", 500
        finally:
            connection.close()

    # retrieve Issue Types & Keywords for the frontend form selection
    cursor.execute("SELECT * FROM IssueType")
    issue_types = cursor.fetchall()

    cursor.execute("SELECT * FROM Keyword")
    keywords = cursor.fetchall()

    connection.close()

    return render_template('form.html', form_title="Create New Ticket", issue_types=issue_types, keywords=keywords)




#***************************************************************************************
# API to update a ticket by Ticket_ID

@app.route('/edit-ticket/<int:ticket_id>', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
       
        status = request.form['status']
        priority = request.form['priority']
        date_resolved = request.form.get('date_resolved') or None

        try:
            
            query = """
                UPDATE Ticket
                SET Status = %s, Priority = %s, Date_resolved = %s
                WHERE Ticket_ID = %s
            """
            cursor.execute(query, (status, priority, date_resolved, ticket_id))
            connection.commit()
            return redirect(url_for('ticket_list'))
        except Exception as e:
            logging.error(f"Error updating ticket ID {ticket_id}: {e}")
            return "An error occurred while updating the ticket.", 500
        finally:
            connection.close()

    
    query = "SELECT * FROM Ticket WHERE Ticket_ID = %s"
    cursor.execute(query, (ticket_id,))
    ticket = cursor.fetchone()
    connection.close()

    if not ticket:
        return "Ticket not found", 404

    return render_template('edit_ticket.html', ticket=ticket)


#********************************************************************
# API to delete a ticket by Ticket_ID

@app.route('/delete-ticket/<int:ticket_id>', methods=['POST'])
def delete_ticket_page(ticket_id):
    """Delete a ticket by its ID and redirect to the home page."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        
        cursor.execute("SELECT COUNT(*) AS count FROM Ticket WHERE Ticket_ID = %s", (ticket_id,))
        if cursor.fetchone()['count'] == 0:
            return "Ticket not found", 404

        # delete ticket
        cursor.execute("DELETE FROM Ticket WHERE Ticket_ID = %s", (ticket_id,))
        connection.commit()
        logging.debug(f"Ticket ID {ticket_id} deleted successfully.")
        return redirect(url_for('home'))
    except Exception as e:
        logging.error(f"Error deleting ticket ID {ticket_id}: {e}")
        return "An error occurred while deleting the ticket.", 500
    finally:
        connection.close()


# API to get 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
