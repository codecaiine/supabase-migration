import os
import json
import sys
import tempfile
import subprocess
import datetime
import threading
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

class LoadingSpinner:
    """Simple loading spinner animation"""
    def __init__(self, message: str = "Loading"):
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.message = message
        self.stop_event = threading.Event()
        self.spinner_thread = None

    def _spin(self):
        """Display spinner animation"""
        i = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{self.message} {self.spinner_chars[i]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(self.spinner_chars)

    def start(self):
        """Start the spinner animation"""
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()

    def stop(self):
        """Stop the spinner animation"""
        self.stop_event.set()
        if self.spinner_thread:
            self.spinner_thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

class SupabaseSchemaMigration:
    """
    Utility to create a complete database schema migration from a Supabase project
    using the Supabase CLI.
    """
    
    def __init__(self, project_id: str, env_name: str, output_dir: str = "migrations", 
                 schemas: Optional[List[str]] = None, clean: bool = False):
        """
        Initialize the migration utility
        
        Args:
            project_id: Supabase project ID/reference
            env_name: Environment name (dev, prod, etc.)
            output_dir: Directory to save migration files
            schemas: Optional list of schemas to pull (e.g., ['auth', 'storage']). If None, pulls all schemas.
            clean: If True, generates a clean schema dump without existing migration history
        """
        self.project_id = project_id
        self.env_name = env_name
        self.output_dir = output_dir
        self.schemas = schemas
        self.clean = clean
        self.temp_dir = tempfile.mkdtemp()
        
        # Generate timestamp for the migration file
        timestamp = datetime.datetime.now()
        date_folder = timestamp.strftime("%Y%m%d")
        time_suffix = timestamp.strftime("%H%M%S")
        
        # Create dated folder path
        self.dated_output_dir = os.path.join(output_dir, date_folder)
        
        # Generate output path with dated folder
        schema_suffix = f"_{'_'.join(schemas)}" if schemas else "_all"
        clean_suffix = "_clean" if clean else ""
        self.output_path = os.path.join(
            self.dated_output_dir,
            f"{time_suffix}_{env_name}{schema_suffix}{clean_suffix}_migration.sql"
        )
        
        # Ensure output directories exist
        Path(self.dated_output_dir).mkdir(parents=True, exist_ok=True)

    def _check_supabase_cli(self) -> bool:
        """Check if Supabase CLI is installed and logged in"""
        try:
            # Check if supabase CLI is installed
            subprocess.run(["supabase", "--version"], 
                         check=True, capture_output=True, text=True, encoding='utf-8')
            
            # Check if user is logged in by trying to list projects
            result = subprocess.run(["supabase", "projects", "list"], 
                                  check=True, capture_output=True, text=True, encoding='utf-8')
            return True
        except subprocess.CalledProcessError as e:
            if "not logged in" in str(e.stderr):
                print("Error: Not logged in to Supabase CLI.")
                print("Please run 'supabase login' with your access token.")
            else:
                print("Error checking Supabase CLI:", str(e))
            return False
        except FileNotFoundError:
            print("Error: Supabase CLI not found.")
            print("Please install it using: npm install -g supabase")
            return False

    def _get_latest_migration(self) -> Optional[str]:
        """Get the latest migration file path for the current date"""
        if not os.path.exists(self.dated_output_dir):
            return None
        
        # Get all migration files in the dated folder
        migration_files = [f for f in os.listdir(self.dated_output_dir) 
                         if f.endswith('_migration.sql')]
        
        if not migration_files:
            return None
            
        # Sort by filename (which includes timestamp)
        latest_file = sorted(migration_files)[-1]
        return os.path.join(self.dated_output_dir, latest_file)

    def _get_schema_hash(self, schema_content: str) -> str:
        """Generate a hash of the schema content"""
        # Remove comments and whitespace for comparison
        clean_content = '\n'.join(line for line in schema_content.split('\n')
                                if not line.strip().startswith('--') and line.strip())
        return hashlib.md5(clean_content.encode()).hexdigest()

    def _compare_with_latest_migration(self, new_schema: str) -> bool:
        """Compare new schema with latest migration to check for changes"""
        latest_migration = self._get_latest_migration()
        if not latest_migration:
            return True  # No previous migration, so this is a new change
            
        try:
            with open(latest_migration, 'r', encoding='utf-8') as f:
                old_schema = f.read()
                
            # Compare hashes of the schemas
            old_hash = self._get_schema_hash(old_schema)
            new_hash = self._get_schema_hash(new_schema)
            
            return old_hash != new_hash
        except Exception as e:
            print(f"Warning: Could not compare with latest migration: {e}")
            return True  # If comparison fails, assume there are changes

    def generate_migration(self) -> bool:
        """Generate the complete schema migration file using Supabase CLI"""
        print(f"Generating schema migration for {self.env_name} environment (project: {self.project_id})")
        if self.schemas:
            print(f"Pulling schemas: {', '.join(self.schemas)}")
        else:
            print("Pulling all schemas")
        if self.clean:
            print("Generating clean schema dump (excluding migration history)")
        
        # Check Supabase CLI first
        if not self._check_supabase_cli():
            return False
        
        try:
            # Get database password from environment
            db_password = os.environ.get(f"SUPABASE_DB_PASSWORD_{self.env_name.upper()}")
            if not db_password:
                print(f"Warning: SUPABASE_DB_PASSWORD_{self.env_name.upper()} not found in environment")
                print("Trying with linked project...")
                use_db_url = False
            else:
                use_db_url = True
            
            # Use supabase db dump command to get schema
            temp_output = os.path.join(self.temp_dir, f"schema_{self.env_name}.sql")
            
            print("Extracting schema using Supabase CLI...")
            
            # Build the command
            cmd = [
                "supabase", "db", "dump",
                "--data-only=false",  # Exclude data, only get schema
            ]
            
            if use_db_url:
                # Use direct database URL
                db_url = f"postgresql://postgres:{db_password}@db.{self.project_id}.supabase.co:5432/postgres"
                cmd.extend(["--db-url", db_url])
                print("Using direct database connection...")
            else:
                # Try with linked project
                print("Using linked project...")
            
            # Add schema filter if specified
            if self.schemas:
                cmd.extend(["-s", ",".join(self.schemas)])
            
            # Add output file
            cmd.extend(["-f", temp_output])
            
            # Debug: print the command (hide password)
            debug_cmd = cmd.copy()
            if use_db_url and "--db-url" in debug_cmd:
                db_url_index = debug_cmd.index("--db-url")
                debug_cmd[db_url_index + 1] = f"postgresql://postgres:****@db.{self.project_id}.supabase.co:5432/postgres"
            print(f"Running command: {' '.join(debug_cmd)}")
            
            # Start loading spinner
            spinner = LoadingSpinner("Extracting schema")
            spinner.start()
            
            try:
                # Run the command with timeout
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
                print(f"Command stdout: {result.stdout}")
                if result.stderr:
                    print(f"Command stderr: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("ERROR: Command timed out after 300 seconds")
                spinner.stop()
                return False
            except subprocess.CalledProcessError as e:
                print(f"Error running command: {e}")
                print(f"Error output: {e.stderr}")
                spinner.stop()
                
                # If direct connection failed, try with debug
                if use_db_url:
                    print("\nTrying with debug flag...")
                    debug_cmd = cmd + ["--debug"]
                    try:
                        debug_result = subprocess.run(debug_cmd, capture_output=True, text=True)
                        print(f"Debug output: {debug_result.stderr}")
                    except:
                        pass
                
                return False
            finally:
                # Stop the spinner
                spinner.stop()
            
            # Add debug to check if file was created and its content
            if os.path.exists(temp_output):
                print(f"Temporary file created: {temp_output}")
                with open(temp_output, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"File size: {len(content)} bytes")
                    print(f"First 500 characters: {content[:500]}")
                    
                    # Debug: check for specific table names
                    print("\nChecking for CREATE TABLE statements:")
                    for line in content.split('\n'):
                        if 'CREATE TABLE' in line:
                            print(f"Found: {line.strip()}")
            else:
                print(f"ERROR: Temporary file not created at {temp_output}")
                return False
            
            # Read the temporary file and write to final destination with headers
            with open(temp_output, 'r', encoding='utf-8') as temp_file:
                schema_content = temp_file.read()
            
            # If clean mode is enabled, remove migration history
            if self.clean:
                # Remove migration history tables and related objects
                schema_content = self._remove_migration_history(schema_content)
            
            # Process the content line by line to handle enum types properly
            processed_lines = []
            in_enum_creation = False
            enum_lines = []
            
            for line in schema_content.split('\n'):
                if 'CREATE TYPE' in line and 'AS ENUM' in line:
                    in_enum_creation = True
                    enum_lines = [line]
                elif in_enum_creation:
                    enum_lines.append(line)
                    if ');' in line:
                        in_enum_creation = False
                        # Convert the enum creation to a safe version
                        enum_content = '\n'.join(enum_lines)
                        safe_enum = f"""
DO $$ 
BEGIN
    {enum_content}
EXCEPTION WHEN duplicate_object THEN null;
END $$;
"""
                        processed_lines.append(safe_enum)
                else:
                    processed_lines.append(line)
            
            # Join the processed lines back together
            schema_content = '\n'.join(processed_lines)
            
            # Check if this schema is different from the latest migration
            if not self._compare_with_latest_migration(schema_content):
                print(f"No changes detected in schema. Skipping migration generation.")
                return True
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                # Add header
                f.write(f"-- Supabase Schema Migration\n")
                f.write(f"-- Environment: {self.env_name}\n")
                f.write(f"-- Project ID: {self.project_id}\n")
                if self.schemas:
                    f.write(f"-- Schemas: {', '.join(self.schemas)}\n")
                if self.clean:
                    f.write("-- Clean schema dump (migration history excluded)\n")
                f.write(f"-- Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                # Write schema content
                f.write(schema_content)
            
            print(f"Successfully wrote schema to {self.output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error generating schema for {self.env_name}:")
            print(f"Command output: {e.stdout}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _remove_migration_history(self, schema_content: str) -> str:
        """Remove migration history tables and related objects from the schema"""
        # List of migration history related objects to remove
        migration_objects = [
            "CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations",
            "CREATE TABLE IF NOT EXISTS supabase_migrations.migrations",
            "CREATE SCHEMA IF NOT EXISTS supabase_migrations",
            "GRANT ALL ON SCHEMA supabase_migrations",
            "GRANT ALL ON ALL TABLES IN SCHEMA supabase_migrations",
            "GRANT ALL ON ALL SEQUENCES IN SCHEMA supabase_migrations",
            "GRANT ALL ON ALL FUNCTIONS IN SCHEMA supabase_migrations"
        ]
        
        # Split content into lines and filter out migration history
        lines = schema_content.split('\n')
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            # Skip lines that start with migration history objects
            if any(line.strip().startswith(obj) for obj in migration_objects):
                skip_next = True
                continue
                
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)


def extract_project_id_from_url(url: str) -> str:
    """Extract project ID from Supabase URL"""
    if not url:
        return ""
    return url.replace("https://", "").split(".")[0]


def get_environment_choice() -> Optional[str]:
    """Display menu and get environment choice from user"""
    print("\nSelect environment to generate migration for:")
    print("1. Production")
    print("2. Allianz")
    print("3. Development")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (0-3): ").strip()
            if choice == "0":
                return None
            elif choice == "1":
                return "prod"
            elif choice == "2":
                return "allianz"
            elif choice == "3":
                return "dev"
            else:
                print("Invalid choice. Please enter a number between 0 and 3.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

def generate_multi_environment_migrations(schemas: Optional[List[str]] = None, clean: bool = False, env_name: Optional[str] = None):
    """Generate migrations for Supabase environments
    
    Args:
        schemas: Optional list of schemas to pull (e.g., ['auth', 'storage']). If None, pulls all schemas.
        clean: If True, generates a clean schema dump without existing migration history
        env_name: Optional environment name to process. If None, will prompt user.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Define environments
    environments = {
        "dev": {
            "name": "dev", 
            "url": os.environ.get("SUPABASE_URL_DEV"),
            "project_id": extract_project_id_from_url(os.environ.get("SUPABASE_URL_DEV", ""))
        },
        "prod": {
            "name": "prod", 
            "url": os.environ.get("SUPABASE_URL_PROD"),
            "project_id": extract_project_id_from_url(os.environ.get("SUPABASE_URL_PROD", ""))
        },
        "allianz": {
            "name": "allianz", 
            "url": os.environ.get("SUPABASE_URL_ALLIANZ"),
            "project_id": extract_project_id_from_url(os.environ.get("SUPABASE_URL_ALLIANZ", ""))
        }
    }
    
    # If no environment specified, show menu
    if env_name is None:
        env_name = get_environment_choice()
        if env_name is None:
            print("Exiting...")
            return False
    
    # Get the selected environment
    env = environments.get(env_name)
    if not env:
        print(f"Invalid environment: {env_name}")
        return False
    
    if not env["url"]:
        print(f"Missing URL for {env['name']} environment")
        return False
    
    output_dir = "migrations"
    
    # Create migrations directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"\n{'='*50}")
        print(f"Processing {env['name']} environment")
        print(f"{'='*50}")
        
        migration = SupabaseSchemaMigration(
            project_id=env["project_id"],
            env_name=env["name"],
            output_dir=output_dir,
            schemas=schemas,
            clean=clean
        )
        
        success = migration.generate_migration()
        
        if success:
            print(f"\nSuccessfully generated migration for {env['name']} environment")
            print(f"Output: {migration.output_path}")
        else:
            print(f"\nFailed to generate migration for {env['name']} environment")
        
        return success
        
    except Exception as e:
        print(f"Error processing {env['name']} environment: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Checking Supabase CLI installation...")
    try:
        version_output = subprocess.run(
            ["supabase", "--version"], 
            check=True, capture_output=True, text=True, encoding='utf-8'
        ).stdout.strip()
        print(f"Found Supabase CLI: {version_output}")
    except FileNotFoundError:
        print("Supabase CLI not found!")
        print("\nTo install Supabase CLI:")
        print("1. Make sure you have Node.js installed")
        print("2. Run: npm install -g supabase")
        print("3. Run: supabase login")
        print("\nAfter installation, run this script again.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error checking Supabase CLI: {e}")
        sys.exit(1)
    
    # Parse command line arguments
    schemas = None
    clean = False
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--schemas":
            schemas = sys.argv[i + 1].split(",")
            i += 2
        elif sys.argv[i] == "--clean":
            clean = True
            i += 1
        else:
            i += 1
    
    if schemas:
        print(f"Pulling specific schemas: {schemas}")
    else:
        print("Pulling all schemas")
    
    if clean:
        print("Generating clean schema dump (excluding migration history)")
    
    # Generate migration for selected environment
    success = generate_multi_environment_migrations(schemas=schemas, clean=clean)
    sys.exit(0 if success else 1)