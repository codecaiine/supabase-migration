# Supabase Schema Migration Tools

A collection of Python utilities to generate and manage database schema migrations from Supabase projects. These tools help you create schema dumps, track schema changes, and manage migrations across different environments.

## Tools Included

This repository contains two main tools:

1. **migra_schema.py** - Generates complete schema migrations from Supabase projects
2. **migra_diff.py** - Compares schemas and generates differential migration scripts

## Features

- Generate complete schema migrations for multiple environments (dev, prod, etc.)
- Pull specific schemas (auth, storage, etc.) or all schemas
- Create clean schema dumps without migration history
- Generate differential migration scripts showing only the changes between versions
- Handle enum types properly to avoid syntax errors
- Support for multiple Supabase projects

## Prerequisites

- Python 3.7+
- Supabase CLI installed (`npm install -g supabase`)
- Supabase CLI logged in (`supabase login`)
- PostgreSQL client tools installed (psql, createdb, dropdb)
- migra Python package installed (`pip install migra[pg]`)
- Environment variables set in `.env` file

## Environment Variables

Create a `.env` file with the following variables:

```env
SUPABASE_URL_DEV=https://your-dev-project.supabase.co
SUPABASE_URL_PROD=https://your-prod-project.supabase.co
SUPABASE_URL_ALLIANZ=https://your-allianz-project.supabase.co
```

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Schema Migration (migra_schema.py)

#### Basic Usage

Generate complete schema migrations for all environments and all schemas:
```bash
python migra_schema.py
```

You'll be prompted to select an environment (Production, Allianz, or Development).

#### Pull Specific Schemas

Generate migrations for specific schemas (e.g., auth and storage):
```bash
python migra_schema.py --schemas auth,storage
```

#### Clean Schema Dump

Generate a clean schema dump without migration history:
```bash
python migra_schema.py --clean
```

#### Combined Options

Generate a clean schema dump for specific schemas:
```bash
python migra_schema.py --clean --schemas auth,storage
```

### Schema Diff Generator (migra_diff.py)

#### Basic Usage

Generate a differential migration script showing only the changes between the latest and previous schema versions:
```bash
python migra_diff.py
```

You'll be prompted to select an environment (Production, Allianz, or Development).

#### Specify Environment

Generate a diff for a specific environment without showing the menu:
```bash
python migra_diff.py --env dev
```

#### Pull Specific Schemas

Generate a diff for specific schemas only:
```bash
python migra_diff.py --schemas auth,storage
```

#### Combined Options

Generate a diff for a specific environment and specific schemas:
```bash
python migra_diff.py --env prod --schemas public,storage
```

## Output Files

### Schema Migrations

The `migra_schema.py` script generates SQL migration files in the `migrations` directory with the following naming convention:
```
migrations/{date}/{timestamp}_{environment}_{schemas}_{clean}_migration.sql
```

Example:
- `migrations/20240501/123456_dev_all_migration.sql` (all schemas)
- `migrations/20240501/123456_dev_auth_storage_migration.sql` (specific schemas)
- `migrations/20240501/123456_dev_all_clean_migration.sql` (clean dump)

### Schema Diffs

The `migra_diff.py` script generates SQL diff files in the `migrations` directory with the following naming convention:
```
migrations/{date}/{timestamp}_{environment}_{schemas}_diff.sql
```

Example:
- `migrations/20240501/123456_dev_all_diff.sql` (all schemas)
- `migrations/20240501/123456_dev_auth_storage_diff.sql` (specific schemas)

## How Schema Diff Works

The `migra_diff.py` script works as follows:

1. Generates a new schema migration using `migra_schema.py`
2. Finds the latest and previous migration files in the migrations directory
3. Creates temporary PostgreSQL databases and loads the schema files into them
4. Uses the `migra` library to generate a SQL script containing only the differences
5. Wraps the diff in a transaction for safety (BEGIN/COMMIT)
6. Cleans up the temporary databases

## What's Included in Clean Dumps

Clean schema dumps exclude:
- `supabase_migrations.schema_migrations` table
- `supabase_migrations.migrations` table
- `supabase_migrations` schema
- All related grants and permissions

## Troubleshooting

### Dependency Issues

1. **Supabase CLI not found**
   - Install Supabase CLI: `npm install -g supabase`
   - Run `supabase login` with your access token

2. **migra package not found**
   - Install migra: `pip install migra[pg]`

3. **PostgreSQL client tools not found**
   - Install PostgreSQL client tools for your operating system

### Permission Issues

1. **Database creation errors**
   - Ensure your PostgreSQL user has permissions to create and drop databases
   - Check PostgreSQL connection settings
   - Ensure no conflicts with existing database names

2. **Supabase access issues**
   - Ensure you have the necessary permissions in your Supabase project
   - Check that your access token has the required scopes

### Environment Issues

1. **Missing environment variables**
   - Ensure all required environment variables are set in `.env`
   - Check that the URLs are correct and accessible

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
