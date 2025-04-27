# Supabase Schema Migration Tool

A Python utility to generate database schema migrations from Supabase projects using the Supabase CLI. This tool helps you create clean schema dumps and manage migrations across different environments.

## Features

- Generate schema migrations for multiple environments (dev, prod, etc.)
- Pull specific schemas (auth, storage, etc.) or all schemas
- Create clean schema dumps without migration history
- Handle enum types properly to avoid syntax errors
- Support for multiple Supabase projects

## Prerequisites

- Python 3.7+
- Supabase CLI installed (`npm install -g supabase`)
- Supabase CLI logged in (`supabase login`)
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

### Basic Usage

Generate migrations for all environments and all schemas:
```bash
python migra_schema.py
```

### Pull Specific Schemas

Generate migrations for specific schemas (e.g., auth and storage):
```bash
python migra_schema.py --schemas auth,storage
```

### Clean Schema Dump

Generate a clean schema dump without migration history:
```bash
python migra_schema.py --clean
```

### Combined Options

Generate a clean schema dump for specific schemas:
```bash
python migra_schema.py --clean --schemas auth,storage
```

## Output

The script generates SQL migration files in the `migrations` directory with the following naming convention:
```
{timestamp}_{environment}_{schemas}_{clean}_migration.sql
```

Example:
- `20240315123456_dev_all_migration.sql` (all schemas)
- `20240315123456_dev_auth_storage_migration.sql` (specific schemas)
- `20240315123456_dev_all_clean_migration.sql` (clean dump, all schemas)
- `20240315123456_dev_auth_storage_clean_migration.sql` (clean dump, specific schemas)

## What's Included in Clean Dumps

Clean schema dumps exclude:
- `supabase_migrations.schema_migrations` table
- `supabase_migrations.migrations` table
- `supabase_migrations` schema
- All related grants and permissions

## Error Handling

The script includes error handling for:
- Supabase CLI installation and login status
- Invalid schema names
- Missing environment variables
- Database connection issues

## Troubleshooting

1. **Supabase CLI not found**
   - Install Supabase CLI: `npm install -g supabase`
   - Run `supabase login` with your access token

2. **Missing environment variables**
   - Ensure all required environment variables are set in `.env`
   - Check that the URLs are correct and accessible

3. **Permission issues**
   - Ensure you have the necessary permissions in your Supabase project
   - Check that your access token has the required scopes

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 