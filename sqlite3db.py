import sqlite3

class FunctionDB:
    """
    A class to manage a SQLite database that stores function information.
    """

    def __init__(self, db_file):
        """
        Initialize the FunctionDB instance.

        :param db_file: The SQLite database file.
        """
        self.db_file = db_file
        self.conn = None
        self._create_connection()
        self._create_table()

    def _create_connection(self):
        """
        Create a database connection to the SQLite database.
        """
        try:
            self.conn = sqlite3.connect(self.db_file)
            print(f"\t > Connected to database: {self.db_file}")
        except sqlite3.Error as e:
            exit(f"\t > Error connecting to database: {e}")

    def _create_table(self):
        """
        Create the function table if it doesn't already exist.
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS function (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            function_index TEXT NOT NULL UNIQUE,
            filepath TEXT NOT NULL,
            token_number INT,
            original_function TEXT,
            optimized_function TEXT
        );
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(create_table_sql)
            print("\t > Table 'function' created or already exists.")
        except sqlite3.Error as e:
            exit(f"\t > Error creating table: {e}")

    def insert_function(self, function_index, filepath, token_number, original_function, optimized_function):
        """
        Insert a new function record into the function table.

        :param function_index: Index of the function.
        :param filepath: Filepath where the function is defined.
        :param token_number: Token number (INT) for the function.
        :param original_function: The original function code as text.
        :param optimized_function: The optimized function code as text.
        :return: The id of the inserted row or None if insertion failed.
        """
        sql = '''
        INSERT INTO function(function_index, filepath, token_number, original_function, optimized_function)
        VALUES(?, ?, ?, ?, ?)
        '''
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (function_index, filepath, token_number, original_function, optimized_function))
            self.conn.commit()
            inserted_id = cursor.lastrowid
            print(f"\t > Inserted function record with id {inserted_id}")
            return inserted_id
        except sqlite3.Error as e:
            exit(f"\t > Error inserting record: {e}")

    def update_optimized_function(self, function_index, new_optimized_function):
        """
        Update the optimized_function column for the specified function record.

        :param function_index: The index of the function to update.
        :param new_optimized_function: The new optimized function code as text.
        :return: True if the update was successful, False otherwise.
        """
        sql = '''
        UPDATE function
        SET optimized_function = ?
        WHERE function_index = ?
        '''
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (new_optimized_function, function_index))
            self.conn.commit()
            if cursor.rowcount == 0:
                print(f"\t > No record found with function index: {function_index}")
                return False
            print(f"\t > Updated optimized function for '{function_index}'.")
            return True
        except sqlite3.Error as e:
            exit(f"\t > Error updating record: {e}")
            return False

    def fetch_function_by_id(self, id):
        """
        Fetch a function record from the database by its id.

        :param id: The id of the function record.
        :return: The function record as a tuple 
                 (id, function_index, filepath, token_number, original_function, optimized_function) 
                 or None if not found.
        """
        sql = "SELECT * FROM function WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (id,))
            row = cursor.fetchone()
            if row is None:
                print(f"\t > No function found with id: {id}")
            return row
        except sqlite3.Error as e:
            input(f"\t > Error fetching record: {e}")
            return None

    def close(self):
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
            print("\t > Database connection closed.")


class DatasetDB:
    def __init__(self, db_name='dataset.db'):
        """
        Initializes the DatasetDatabase class by creating (or connecting to) 
        the specified SQLite database and ensuring the `dataset` table exists.
        """
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        """
        Creates the `dataset` table if it doesn't already exist.
        The new table schema:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - model: TEXT NOT NULL
        - interval: INTEGER NOT NULL
        - label: TEXT
        - diff: TEXT
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                interval INTEGER NOT NULL,
                label TEXT,
                diff TEXT
            )
        ''')
        self.connection.commit()

    def insert_record(self, model, interval, label, diff):
        """
        Inserts a new record into the `dataset` table.
        
        :param model: The model name or identifier (TEXT)
        :param interval: The interval value (INTEGER)
        :param label: The label (TEXT)
        :param diff: The difference information (TEXT)
        """
        self.cursor.execute('''
            INSERT INTO dataset (model, interval, label, diff)
            VALUES (?, ?, ?, ?)
        ''', (model, interval, label, diff))
        self.connection.commit()

    def fetch_record_by_model_and_interval(self, model, interval):
        """
        Fetches records from the `dataset` table based on model name and interval.
        
        :param model: The model name to filter (TEXT)
        :param interval: The interval value to filter (INTEGER)
        :return: List of matching records
        """
        self.cursor.execute('''
            SELECT * FROM dataset WHERE model = ? AND interval = ?
        ''', (model, interval))
        return self.cursor.fetchall()

    def fetch_record_by_model_interval_and_id(self, model, interval, id):
        """
        Fetches a record from the `dataset` table based on model name, interval, and primary key id.
        
        :param model: The model name to filter (TEXT)
        :param interval: The interval value to filter (INTEGER)
        :param id: The primary key id to filter (INTEGER)
        :return: The matching record, or None if not found
        """
        self.cursor.execute('''
            SELECT * FROM dataset WHERE model = ? AND interval = ? AND id = ?
        ''', (model, interval, id))
        return self.cursor.fetchone()

    def __del__(self):
        """
        Ensures the database connection is closed when the DatasetDatabase object is deleted.
        """
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

class TestResultDB:
    def __init__(self, db_name):
        """
        Initializes the TestResultDB_PHPSRC class by creating (or connecting to)
        the specified SQLite database and ensuring the `dataset` table exists.
        """
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        """
        Creates the `dataset` table if it doesn't already exist.
        The new table schema:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - iteration: INTEGER
        - total: INTEGER
        - pass: INTEGER
        - fail: INTEGER
        - skip: INTEGER
        - bork: INTEGER
        - testlog: TEXT
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iteration INTEGER,
                total INTEGER,
                pass INTEGER,
                fail INTEGER,
                skip INTEGER,
                bork INTEGER,
                testlog TEXT
            )
        ''')
        self.connection.commit()

    def insert_record(self, iteration, total, pass_count, fail_count, skip_count, bork_count, testlog):
        """
        Inserts a new record into the `dataset` table.
        
        :param iteration: The iteration number (INTEGER)
        :param total:     The total number of tests (INTEGER)
        :param pass_count: The number of passing tests (INTEGER)
        :param fail_count: The number of failing tests (INTEGER)
        :param skip_count: The number of skipped tests (INTEGER)
        :param bork_count: The number of borked tests (INTEGER)
        :param testlog:    Additional test log or notes (TEXT)
        """
        self.cursor.execute('''
            INSERT INTO dataset (iteration, total, pass, fail, skip, bork, testlog)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (iteration, total, pass_count, fail_count, skip_count, bork_count, testlog))
        self.connection.commit()

    def fetch_record_by_id(self, record_id):
        """
        Fetches a record from the `dataset` table by its ID.
        
        :param record_id: The ID of the record to fetch (INTEGER)
        :return: A dictionary containing the record data or None if not found.
        """
        self.cursor.execute('''
            SELECT * FROM dataset WHERE id = ?
        ''', (record_id,))
        return self.cursor.fetchone()

    def __del__(self):
        """
        Ensures the database connection is closed when the TestResultDB_PHPSRC object is deleted.
        """
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

class FuzzResultDB:
    def __init__(self, db_name):
        """
        Initializes the FuzzResultDB class by creating (or connecting to)
        the specified SQLite database and ensuring the `fuzz` table exists.
        """
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self._create_table()  # Make sure to call the correct table creation method

    def _create_table(self) -> None:
        """
        Create the `fuzz` table with columns:
            - id: primary key (auto-incrementing integer)
            - crashsite: text (unique)
            - details: text
            - poc: text
            - poc_env: text
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fuzz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crashsite TEXT UNIQUE,
                details TEXT,
                poc TEXT,
                poc_env TEXT
            )
        ''')
        self.connection.commit()

    def insert_record(self, crashsite, details, poc, poc_env):
        """
        Inserts a new record into the `fuzz` table.
        
        :param crashsite: A unique string identifying the crash site (TEXT)
        :param details:   Additional details about the crash (TEXT)
        :param poc:       Proof of concept data (TEXT)
        :param poc_env:   Environment or configuration info for the POC (TEXT)
        """
        self.cursor.execute('''
            INSERT INTO fuzz (crashsite, details, poc, poc_env)
            VALUES (?, ?, ?, ?)
        ''', (crashsite, details, poc, poc_env))
        self.connection.commit()

    def __del__(self):
        """
        Ensures the database connection is closed when the FuzzResultDB object is deleted.
        """
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
