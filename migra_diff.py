#!/usr/bin/env python3
import os
import sys
import tempfile
import subprocess
import datetime
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Import from existing script
from migra_schema import (
    SupabaseSchemaMigration,
    extract_project_id_from_url, 
    get_environment_choice,
    LoadingSpinner
)
from dotenv import load_dotenv

class SchemaDiffGenerator:
    """
    Utility to generate schema difference scripts between Supabase migrations
    using migra - the PostgreSQL schema migration tool.
    """
    
    def __init__(self, project_id: str, env_name: str, output_dir: str = "migrations",
                 schemas: Optional[List[str]] = None):
        """
        Initialize the schema diff generator
        
        Args:
            project_id: Supabase project ID/reference
            env_name: Environment name (dev, prod, etc.)
            output_dir: Directory to save diff files
            schemas: Optional list of schemas to pull (e.g., ['auth', 'storage']). If None, pulls all schemas.
        """
        self.project_id = project_id
        self.env_name = env_name
        self.output_dir = output_dir
        self.schemas = schemas
        self.temp_dir = tempfile.mkdtemp()
        
        # Generate timestamp for the diff file
        timestamp = datetime.datetime.now()
        date_folder = timestamp.strftime("%Y%m%d")
        time_suffix = timestamp.strftime("%H%M%S")
        
        # Create dated folder path
        self.dated_output_dir = os.path.join(output_dir, date_folder)
        
        # Generate output path with dated folder
        schema_suffix = f"_{'_'.join(schemas)}" if schemas else "_all"
        self.output_path = os.path.join(
            self.dated_output_dir,
            f"{time_suffix}_{env_name}{schema_suffix}_diff.sql"
        )
        
        # Ensure output directories exist
        Path(self.dated_output_dir).mkdir(parents=True, exist_ok=True)
    
    def _check_migra_installation(self) -> bool:
        """Check if migra is installed"""
        try:
            # Check if migra is installed
            subprocess.run(["pip", "show", "migra"], 
                         check=True, capture_output=True, text=True, encoding='utf-8')
            return True
        except subprocess.CalledProcessError:
            print("Error: migra package not found.")
            print("Please install it using: pip install migra[pg]")
            return False
        except Exception as e:
            print(f"Error checking migra installation: {str(e)}")
            return False
    
    def _find_latest_migration_files(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the latest and previous migration files in the migrations directory
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (latest_file_path, previous_file_path)
        """
        if not os.path.exists(self.output_dir):
            return None, None
        
        # Get all date folders
        date_folders = [f for f in os.listdir(self.output_dir) 
                       if os.path.isdir(os.path.join(self.output_dir, f)) and re.match(r'^\d{8}$', f)]
        
        if not date_folders:
            return None, None
        
        # Sort date folders in descending order
        date_folders.sort(reverse=True)
        
        latest_file = None
        previous_file = None
        
        # Find the latest migration file
        for folder in date_folders:
            folder_path = os.path.join(self.output_dir, folder)
            migration_files = [f for f in os.listdir(folder_path) 
                              if f.endswith('_migration.sql') and self.env_name in f]
            
            if not migration_files:
                continue
            
            # Sort by filename (which includes timestamp)
            migration_files.sort(reverse=True)
            
            if latest_file is None:
                latest_file = os.path.join(folder_path, migration_files[0])
                
                # If there's another file in the same folder
                if len(migration_files) > 1:
                    previous_file = os.path.join(folder_path, migration_files[1])
                    return latest_file, previous_file
            else:
                previous_file = os.path.join(folder_path, migration_files[0])
                return latest_file, previous_file
        
        # If we only found one file
        return latest_file, None
    
    def _create_temporary_databases(self, latest_file: str, previous_file: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Create temporary PostgreSQL databases and load schema files into them
        
        Args:
            latest_file: Path to the latest migration file
            previous_file: Path to the previous migration file or None
            
        Returns:
            Tuple[str, Optional[str]]: (latest_db_name, previous_db_name)
        """
        latest_db_name = f"temp_migra_latest_{self.env_name}_{int(datetime.datetime.now().timestamp())}"
        previous_db_name = None
        
        spinner = LoadingSpinner("Setting up temporary databases")
        spinner.start()
        
        try:
            # Create the latest schema database
            subprocess.run(
                ["createdb", latest_db_name],
                check=True, capture_output=True, text=True
            )
            
            # Load the latest schema
            with open(latest_file, 'r', encoding='utf-8') as f:
                latest_schema = f.read()
                
            subprocess.run(
                ["psql", "-d", latest_db_name, "-c", latest_schema],
                check=True, capture_output=True, text=True
            )
            
            # If there's a previous file, create and load that too
            if previous_file:
                previous_db_name = f"temp_migra_prev_{self.env_name}_{int(datetime.datetime.now().timestamp())}"
                
                subprocess.run(
                    ["createdb", previous_db_name],
                    check=True, capture_output=True, text=True
                )
                
                with open(previous_file, 'r', encoding='utf-8') as f:
                    previous_schema = f.read()
                    
                subprocess.run(
                    ["psql", "-d", previous_db_name, "-c", previous_schema],
                    check=True, capture_output=True, text=True
                )
            
            return latest_db_name, previous_db_name
        
        except subprocess.CalledProcessError as e:
            print(f"Error creating temporary databases: {e}")
            if latest_db_name:
                self._cleanup_database(latest_db_name)
            if previous_db_name:
                self._cleanup_database(previous_db_name)
            raise
        finally:
            spinner.stop()
    
    def _cleanup_database(self, db_name: str):
        """Drop a temporary database"""
        try:
            # Disconnect all users first to avoid "database is being accessed by other users" error
            disconnect_sql = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_name}';"
            subprocess.run(
                ["psql", "-d", "postgres", "-c", disconnect_sql],
                check=True, capture_output=True, text=True
            )
            
            # Drop the database
            subprocess.run(
                ["dropdb", db_name],
                check=True, capture_output=True, text=True
            )
        except Exception as e:
            print(f"Warning: Could not clean up database {db_name}: {e}")
    
    def _generate_schema(self) -> bool:
        """Generate a new schema migration first"""
        try:
            # Create a SupabaseSchemaMigration instance and generate the schema
            migration = SupabaseSchemaMigration(
                project_id=self.project_id,
                env_name=self.env_name,
                output_dir=self.output_dir,
                schemas=self.schemas,
                clean=False  # We want the full schema for diffing
            )
            
            success = migration.generate_migration()
            if not success:
                print("Failed to generate schema migration")
                return False
            
            return True
        except Exception as e:
            print(f"Error generating schema: {e}")
            return False

    def generate_diff(self) -> bool:
        """
        Generate a schema difference file between the latest and previous migrations
        
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"Generating schema diff for {self.env_name} environment (project: {self.project_id})")
        
        # Check if migra is installed
        if not self._check_migra_installation():
            return False
        
        # Generate a new schema first
        if not self._generate_schema():
            return False
        
        try:
            # Find the latest migration files
            latest_file, previous_file = self._find_latest_migration_files()
            
            if not latest_file:
                print("No migration files found. Please generate a schema first.")
                return False
            
            if not previous_file:
                print("Only one migration file found. Cannot generate diff.")
                print(f"Latest migration file: {latest_file}")
                return False
            
            print(f"Latest migration: {os.path.basename(latest_file)}")
            print(f"Previous migration: {os.path.basename(previous_file)}")
            
            # Create temporary databases and load schemas
            latest_db, previous_db = self._create_temporary_databases(latest_file, previous_file)
            
            try:
                # Generate diff using migra
                print("Generating schema diff...")
                
                spinner = LoadingSpinner("Generating diff")
                spinner.start()
                
                try:
                    # Run migra to generate diff
                    result = subprocess.run(
                        ["migra", f"postgresql:///{previous_db}", f"postgresql:///{latest_db}"],
                        check=True, capture_output=True, text=True, encoding='utf-8'
                    )
                    
                    diff_content = result.stdout
                    
                    # If no changes, return early
                    if not diff_content or diff_content.strip() == "":
                        print("No schema differences found between the migrations.")
                        return True
                    
                    # Write the diff file
                    with open(self.output_path, 'w', encoding='utf-8') as f:
                        # Add header
                        f.write(f"-- Supabase Schema Diff\n")
                        f.write(f"-- Environment: {self.env_name}\n")
                        f.write(f"-- Project ID: {self.project_id}\n")
                        if self.schemas:
                            f.write(f"-- Schemas: {', '.join(self.schemas)}\n")
                        f.write(f"-- Base: {os.path.basename(previous_file)}\n")
                        f.write(f"-- Target: {os.path.basename(latest_file)}\n")
                        f.write(f"-- Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        # Add migration safety wrapper
                        f.write("-- Start transaction for safety\n")
                        f.write("BEGIN;\n\n")
                        # Write diff content
                        f.write(diff_content)
                        # Add commit
                        f.write("\n-- Commit the changes\nCOMMIT;\n")
                    
                    print(f"Successfully wrote schema diff to {self.output_path}")
                    return True
                
                finally:
                    spinner.stop()
            
            finally:
                # Clean up temporary databases
                if latest_db:
                    print(f"Cleaning up temporary database: {latest_db}")
                    self._cleanup_database(latest_db)
                if previous_db:
                    print(f"Cleaning up temporary database: {previous_db}")
                    self._cleanup_database(previous_db)
                
        except Exception as e:
            print(f"Error generating diff: {e}")
            return False


def generate_diff_for_environment(schemas: Optional[List[str]] = None, env_name: Optional[str] = None):
    """Generate schema diff for Supabase environment
    
    Args:
        schemas: Optional list of schemas to pull (e.g., ['auth', 'storage']). If None, pulls all schemas.
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
        print(f"Processing {env['name']} environment for diff")
        print(f"{'='*50}")
        
        diff_generator = SchemaDiffGenerator(
            project_id=env["project_id"],
            env_name=env["name"],
            output_dir=output_dir,
            schemas=schemas
        )
        
        success = diff_generator.generate_diff()
        
        if success:
            print(f"\nSuccessfully generated diff for {env['name']} environment")
            print(f"Output: {diff_generator.output_path}")
        else:
            print(f"\nFailed to generate diff for {env['name']} environment")
        
        return success
        
    except Exception as e:
        print(f"Error processing {env['name']} environment: {e}")
        return False


if __name__ == "__main__":
    print("Schema Diff Generator for Supabase")
    print("---------------------------------")
    
    # Verify dependencies
    print("Checking dependencies...")
    
    # Check for migra
    try:
        subprocess.run(["pip", "show", "migra"], check=True, capture_output=True, text=True)
        print("✓ migra is installed")
    except subprocess.CalledProcessError:
        print("✗ migra is not installed")
        print("\nTo install migra:")
        print("  pip install migra[pg]")
        sys.exit(1)
    
    # Check for PostgreSQL client tools
    try:
        subprocess.run(["psql", "--version"], check=True, capture_output=True, text=True)
        print("✓ PostgreSQL client tools are installed")
    except FileNotFoundError:
        print("✗ PostgreSQL client tools not found!")
        print("\nPlease install PostgreSQL client tools before continuing.")
        sys.exit(1)
    
    # Check for Supabase CLI
    try:
        version_output = subprocess.run(
            ["supabase", "--version"], 
            check=True, capture_output=True, text=True, encoding='utf-8'
        ).stdout.strip()
        print(f"✓ Supabase CLI: {version_output}")
    except FileNotFoundError:
        print("✗ Supabase CLI not found!")
        print("\nTo install Supabase CLI:")
        print("1. Make sure you have Node.js installed")
        print("2. Run: npm install -g supabase")
        print("3. Run: supabase login")
        sys.exit(1)
    
    # Parse command line arguments
    schemas = None
    env_name = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--schemas":
            schemas = sys.argv[i + 1].split(",")
            i += 2
        elif sys.argv[i] == "--env":
            env_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if schemas:
        print(f"Pulling specific schemas: {schemas}")
    else:
        print("Pulling all schemas")
    
    # Generate diff for selected environment
    success = generate_diff_for_environment(schemas=schemas, env_name=env_name)
    sys.exit(0 if success else 1)