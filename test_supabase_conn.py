import psycopg2
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env
load_dotenv()

def test_connection():
    """Test different connection methods to Supabase"""
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL_DEV")
    db_password = os.getenv("SUPABASE_DB_PASSWORD_DEV")
    
    if not supabase_url or not db_password:
        print("Error: Missing SUPABASE_URL_DEV or SUPABASE_DB_PASSWORD_DEV in .env file")
        return
    
    # Extract project ID from URL
    project_id = supabase_url.replace("https://", "").split(".")[0]
    print(f"Project ID: {project_id}")
    
    # Different database URL formats to try
    database_urls = [
        # Format 1: Direct database URL (common format)
        f"postgresql://postgres:{db_password}@db.{project_id}.supabase.co:5432/postgres",
        
        # Format 2: Pooler URL (for connection pooling)
        f"postgresql://postgres.{project_id}:{db_password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
        
        # Format 3: Alternative pooler URL
        f"postgresql://postgres:{db_password}@pooler.{project_id}.supabase.com:5432/postgres",
        
        # Format 4: Without project prefix in username
        f"postgresql://postgres:{db_password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
    ]
    
    # Try DATABASE_URL from environment if it exists
    if os.getenv("DATABASE_URL"):
        database_urls.insert(0, os.getenv("DATABASE_URL"))
    
    successful_url = None
    
    for i, db_url in enumerate(database_urls, 1):
        print(f"\nTesting connection format {i}...")
        # Mask password for display
        masked_url = db_url.replace(db_password, "*" * 8)
        print(f"URL: {masked_url}")
        
        try:
            # Parse the URL to get connection parameters
            parsed_url = urllib.parse.urlparse(db_url)
            
            connection = psycopg2.connect(
                dbname=parsed_url.path[1:],  # Remove leading '/'
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port
            )
            
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
        print(successful_url.replace(db_password, "*" * 8))
        print("\nYou can use this format in your migration script.")
        
        # Save the working URL to a file for reference
        with open("working_db_url.txt", "w") as f:
            f.write(f"# Working database URL for project {project_id}\n")
            f.write(f"DATABASE_URL={successful_url}\n")
        
        print("\nWorking URL saved to: working_db_url.txt")
    else:
        print("\n" + "="*50)
        print("ERROR: Could not establish a connection with any format.")
        print("\nPlease check:")
        print("1. Your SUPABASE_DB_PASSWORD_DEV is correct")
        print("2. Your SUPABASE_URL_DEV is correct")
        print("3. Your project exists and is accessible")
        print("\nYou might need to:")
        print("- Reset your database password in Supabase dashboard")
        print("- Check if your IP is allowed in database settings")
        print("- Verify the project reference ID")

if __name__ == "__main__":
    print("Testing Supabase database connections...")
    test_connection()