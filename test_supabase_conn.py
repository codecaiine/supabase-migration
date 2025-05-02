import psycopg2
import os
from dotenv import load_dotenv
import urllib.parse
import requests

# Load environment variables from .env
load_dotenv()

def check_supabase_project(project_id):
    """Check if Supabase project exists by checking the API"""
    try:
        # Try to access the project's API endpoint
        url = f"https://{project_id}.supabase.co"
        response = requests.get(f"{url}/rest/v1/", timeout=5)
        if response.status_code in [200, 401, 403]:  # Project exists
            return True
        return False
    except:
        return False

def get_connection_info():
    """Get connection information from Supabase dashboard format"""
    print("\nSupabase Connection String Helper")
    print("="*50)
    print("Please go to your Supabase project dashboard:")
    print("1. Click on the Settings icon (gear)")
    print("2. Click on 'Database' in the sidebar")
    print("3. Find the 'Connection string' section")
    print("4. Copy the connection string (it looks like: postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres)")
    print("\nPaste your connection string here (or press Enter to skip): ")
    connection_string = input().strip()
    
    if connection_string:
        # Parse the connection string
        try:
            parsed = urllib.parse.urlparse(connection_string)
            password = parsed.password
            hostname = parsed.hostname
            
            # Extract project ID from hostname
            if hostname and ".supabase.co" in hostname:
                project_id = hostname.split('.')[1] if hostname.startswith('db.') else hostname.split('.')[0]
                return project_id, password, connection_string
        except:
            print("Could not parse the connection string.")
    
    return None, None, None

def test_connection_comprehensive():
    """Comprehensive connection testing with multiple formats"""
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL_DEV")
    db_password = os.getenv("SUPABASE_DB_PASSWORD_DEV")
    
    # Get connection info from user if needed
    dashboard_project_id, dashboard_password, dashboard_url = get_connection_info()
    
    if dashboard_url:
        print(f"\nUsing dashboard connection info: {dashboard_url.replace(dashboard_password, '*' * 8)}")
        db_password = dashboard_password
        project_id = dashboard_project_id
    else:
        if not supabase_url or not db_password:
            print("Error: Missing SUPABASE_URL_DEV or SUPABASE_DB_PASSWORD_DEV in .env file")
            return
        
        # Extract project ID from URL
        project_id = supabase_url.replace("https://", "").split(".")[0]
    
    print(f"\nProject ID: {project_id}")
    
    # Check if project exists
    print(f"Checking if project exists...")
    if check_supabase_project(project_id):
        print("✓ Project found!")
    else:
        print("✗ Project not found or not accessible")
    
    # Comprehensive list of database URL formats to try
    database_urls = [
        # Dashboard provided URL
        dashboard_url,
        
        # Format 1: Standard direct database URL
        f"postgresql://postgres:{db_password}@db.{project_id}.supabase.co:5432/postgres",
        
        # Format 2: Pooler URL with project prefix in username
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
        
        # Format 3: Alternative region pooler URLs
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-eu-central-1.pooler.supabase.com:5432/postgres",
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
        
        # Format 4: Direct connection with port 6543 (pgbouncer)
        f"postgresql://postgres:{db_password}@db.{project_id}.supabase.co:6543/postgres",
        
        # Format 5: Pooler without project prefix
        f"postgresql://postgres:{db_password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
        
        # Format 6: Session pooling mode
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres?pgbouncer=true",
        
        # Format 7: Transaction pooling mode  
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres?pgbouncer=true&connection_limit=10",
    ]
    
    # Try DATABASE_URL from environment if it exists
    if os.getenv("DATABASE_URL"):
        database_urls.insert(0, os.getenv("DATABASE_URL"))
    
    # Remove None values
    database_urls = [url for url in database_urls if url]
    
    successful_url = None
    
    for i, db_url in enumerate(database_urls, 1):
        print(f"\nTesting connection format {i}...")
        # Mask password for display
        masked_url = db_url.replace(db_password, "*" * 8) if db_password else db_url
        print(f"URL: {masked_url}")
        
        try:
            # Parse the URL to get connection parameters
            parsed_url = urllib.parse.urlparse(db_url)
            
            # Extract query parameters
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Basic connection parameters
            connection_params = {
                'dbname': parsed_url.path[1:],  # Remove leading '/'
                'user': parsed_url.username,
                'password': parsed_url.password,
                'host': parsed_url.hostname,
                'port': parsed_url.port or 5432
            }
            
            # Add SSL mode if not local
            if not parsed_url.hostname.startswith('localhost'):
                connection_params['sslmode'] = 'require'
            
            connection = psycopg2.connect(**connection_params)
            
            print("✓ Connection successful!")
            
            # Test query
            cursor = connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"PostgreSQL version: {version}")
            
            # Get some basic info
            cursor.execute("SELECT current_database(), current_user;")
            db_info = cursor.fetchone()
            print(f"Database: {db_info[0]}, User: {db_info[1]}")
            
            cursor.close()
            connection.close()
            
            successful_url = db_url
            break
            
        except Exception as e:
            print(f"✗ Connection failed: {str(e)}")
    
    if successful_url:
        print("\n" + "="*50)
        print("SUCCESS! Working database URL format:")
        masked_success_url = successful_url.replace(db_password, "*" * 8) if db_password else successful_url
        print(masked_success_url)
        print("\nYou can use this format in your migration script.")
        
        # Save the working URL to a file for reference
        with open("working_db_url.txt", "w") as f:
            f.write(f"# Working database URL for project {project_id}\n")
            f.write(f"DATABASE_URL={successful_url}\n")
        
        print("\nWorking URL saved to: working_db_url.txt")
        
        # Also update the .env file example
        print("\nAdd this to your .env file:")
        print(f"DATABASE_URL={successful_url}")
        print(f"SUPABASE_DB_PASSWORD_DEV={db_password}")
        
    else:
        print("\n" + "="*50)
        print("ERROR: Could not establish a connection with any format.")
        print("\nTroubleshooting steps:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to Settings > Database")
        print("3. Copy the connection string from 'Connection string' section")
        print("4. Check if the database password is correct")
        print("5. Try resetting the database password if needed")
        print("6. Verify your project ID is correct")
        print("7. Check if your IP needs to be whitelisted")
        
        print("\nDiagnostic Information:")
        print(f"Project ID detected: {project_id}")
        print(f"Password length: {len(db_password) if db_password else 0} characters")
        print(f"Project URL: https://{project_id}.supabase.co")

if __name__ == "__main__":
    print("Enhanced Supabase Connection Debugger")
    print("="*50)
    
    # Install requests if needed
    try:
        import requests
    except ImportError:
        print("Installing requests library...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    test_connection_comprehensive()