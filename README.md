# Supabase Schema Migration Toolkit

![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

A comprehensive toolkit for managing database schema migrations in Supabase projects. This toolkit provides enterprise-grade utilities for schema extraction, comparison, and deployment across multiple environments.

## 📋 Overview

The Supabase Schema Migration Toolkit offers robust solutions for DevOps and database administration teams working with Supabase projects. It simplifies schema management with:

- **Full Schema Extraction** - Capture complete database schemas from any Supabase environment
- **Differential Migration Generation** - Automatically identify and script only the changes between schema versions
- **Multi-Environment Support** - Seamlessly work across development, staging, and production environments
- **Schema-Specific Controls** - Target specific schemas for fine-grained migration management

## 🛠️ Components

This toolkit contains two primary utilities:

| Tool | Description |
|------|-------------|
| **migra_schema.py** | Extracts complete schema snapshots from Supabase environments |
| **migra_diff.py** | Generates differential migration scripts by comparing schema versions |

## ✨ Key Features

- **Enterprise Multi-Environment Support**: Manage schemas across development, production, and custom environments
- **Selective Schema Extraction**: Target specific schemas (auth, storage, public, etc.) or extract all schemas
- **Clean Schema Generation**: Option to exclude migration history metadata for cleaner deployments
- **Differential Change Detection**: Identify and script only the schema changes between versions
- **Safe Migration Scripts**: All differential scripts wrapped in transactions for safe execution
- **Comprehensive Documentation**: Automatically documented migrations with environment details and timestamps
- **Automatic Dependency Checking**: Verify all required tools are properly installed
- **Progress Visualization**: Visual indicators for long-running operations

## 🔧 Prerequisites

- **Python 3.7+**
- **Supabase CLI**
  - Installation: `npm install -g supabase`
  - Authentication: `supabase login`
- **PostgreSQL Client Tools**
  - `psql`, `createdb`, and `dropdb` commands available in PATH
- **Python Dependencies**
  - `migra[pg]`: PostgreSQL schema comparison library
  - `python-dotenv`: Environment variable management
  - Additional requirements in `requirements.txt`

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/supabase-schema-toolkit.git
   cd supabase-schema-toolkit
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase project URLs
   ```

## ⚙️ Configuration

Create a `.env` file with your Supabase environment URLs:

```ini
# Supabase Project URLs
SUPABASE_URL_DEV=https://your-dev-project.supabase.co
SUPABASE_URL_PROD=https://your-prod-project.supabase.co
SUPABASE_URL_ALLIANZ=https://your-allianz-project.supabase.co

# Optional: PostgreSQL connection overrides if needed
# PG_HOST=localhost
# PG_PORT=5432
# PG_USER=postgres
```

## 📖 Usage Guide

### Schema Extraction (migra_schema.py)

Extract complete database schemas from Supabase environments.

#### Basic Usage

```bash
python migra_schema.py
```
This launches an interactive menu to select the target environment.

#### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--schemas` | Comma-separated list of schemas to extract | `--schemas auth,storage,public` |
| `--clean` | Generate schema without migration history | `--clean` |
| `--env` | Specify environment (bypasses menu) | `--env dev` |

#### Examples

Extract all schemas from production:
```bash
python migra_schema.py --env prod
```

Extract specific schemas with clean output:
```bash
python migra_schema.py --schemas public,auth --clean --env dev
```

### Differential Migration (migra_diff.py)

Generate schema migration scripts containing only the changes between versions.

#### Basic Usage

```bash
python migra_diff.py
```
This launches an interactive menu to select the target environment.

#### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--schemas` | Comma-separated list of schemas to compare | `--schemas public,storage` |
| `--env` | Specify environment (bypasses menu) | `--env prod` |

#### Examples

Generate diff for all schemas in development:
```bash
python migra_diff.py --env dev
```

Generate diff for specific schemas in production:
```bash
python migra_diff.py --schemas auth,public --env prod
```

## 📂 Output Structure

The toolkit organizes migrations in a date-based folder structure:

```
migrations/
├── 20240501/                  # Date folder (YYYYMMDD)
│   ├── 093045_dev_all_migration.sql      # Complete schema
│   ├── 093045_dev_all_diff.sql           # Differential schema
│   ├── 162230_prod_all_migration.sql     # Production schema
│   └── 162230_prod_public_diff.sql       # Production public schema diff
└── 20240502/
    └── ...
```

### Filename Convention

- **Schema Migrations**: `{timestamp}_{environment}_{schemas}_{clean}_migration.sql`
- **Schema Diffs**: `{timestamp}_{environment}_{schemas}_diff.sql`

## 🔄 How Schema Diff Works

The differential migration process follows these steps:

1. **Schema Extraction**: Generate a fresh schema snapshot using the Supabase CLI
2. **Version Identification**: Locate the latest and previous schema snapshots
3. **Database Staging**: Create temporary PostgreSQL databases for comparison
4. **Differential Analysis**: Use `migra` to identify schema differences
5. **Script Generation**: Create a SQL script with only the necessary changes
6. **Safety Implementation**: Wrap changes in a transaction for safe execution
7. **Resource Cleanup**: Remove temporary databases automatically

## 📝 Clean Schema Specification

When using the `--clean` option, the following objects are automatically excluded:

- `supabase_migrations.schema_migrations` table
- `supabase_migrations.migrations` table
- `supabase_migrations` schema itself
- All related grants and permissions
- Any migration tracking metadata

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Supabase CLI not found** | Install with `npm install -g supabase` and authenticate with `supabase login` |
| **PostgreSQL client tools missing** | Install PostgreSQL client tools for your OS and ensure they're in your PATH |
| **Database creation permission errors** | Ensure your PostgreSQL user has CREATEDB privilege |
| **Missing environment variables** | Verify `.env` file contains all required Supabase URLs |

### Diagnostic Commands

Check Supabase CLI installation:
```bash
supabase --version
```

Verify migra installation:
```bash
pip show migra
```

Test PostgreSQL connectivity:
```bash
psql -c "SELECT version();"
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📬 Contact

For questions or support, please open an issue in the repository.

---

**Built with ❤️ for the Supabase community**
