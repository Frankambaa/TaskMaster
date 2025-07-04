# Database Configuration Guide

This guide explains how to configure different databases for your RAG chatbot application.

## Supported Databases

1. **SQLite** (Default for local development)
2. **PostgreSQL** (Cloud/Production)
3. **MySQL** (Local and Cloud)

## Configuration Options

The application automatically detects the database type based on environment variables in this priority order:

1. `MYSQL_DATABASE_URL` - Use MySQL database
2. `DATABASE_URL` - Use PostgreSQL database  
3. **Default** - Use SQLite for local development

## Local Database Setup

### Option 1: SQLite (Easiest - No setup required)

SQLite is used by default if no database URL is provided. The database file `chatbot.db` will be created automatically in your project directory.

**Pros:**
- No installation required
- Perfect for development and testing
- Database file is portable

**Cons:**
- Not suitable for production with multiple users
- Limited concurrent access

### Option 2: Local MySQL Setup

#### Step 1: Install MySQL

**On Windows:**
1. Download MySQL installer from https://dev.mysql.com/downloads/installer/
2. Run the installer and select "MySQL Server" and "MySQL Workbench"
3. Set root password during installation

**On macOS:**
```bash
# Using Homebrew
brew install mysql
brew services start mysql

# Set root password
mysql_secure_installation
```

**On Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# Set root password
sudo mysql_secure_installation
```

#### Step 2: Create Database and User

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE chatbot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (replace 'password' with your preferred password)
CREATE USER 'chatbot_user'@'localhost' IDENTIFIED BY 'your_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON chatbot_db.* TO 'chatbot_user'@'localhost';
FLUSH PRIVILEGES;

-- Exit MySQL
EXIT;
```

#### Step 3: Set Environment Variable

Create a `.env` file in your project root:

```bash
# For MySQL
MYSQL_DATABASE_URL=mysql+pymysql://chatbot_user:your_password_here@localhost:3306/chatbot_db

# Other required variables
OPENAI_API_KEY=your_openai_api_key_here
SESSION_SECRET=your_session_secret_here
```

### Option 3: Local PostgreSQL Setup

#### Step 1: Install PostgreSQL

**On Windows:**
1. Download from https://www.postgresql.org/download/windows/
2. Run installer and remember the password for 'postgres' user

**On macOS:**
```bash
# Using Homebrew
brew install postgresql
brew services start postgresql

# Create database user
createuser --interactive
```

**On Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Step 2: Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE chatbot_db;
CREATE USER chatbot_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
\q
```

#### Step 3: Set Environment Variable

```bash
# For PostgreSQL
DATABASE_URL=postgresql://chatbot_user:your_password_here@localhost:5432/chatbot_db

# Other required variables
OPENAI_API_KEY=your_openai_api_key_here
SESSION_SECRET=your_session_secret_here
```

## Cloud Database Options

### MySQL Cloud Providers

1. **PlanetScale** (Free tier available)
   ```
   MYSQL_DATABASE_URL=mysql://username:password@host:port/database?sslmode=require
   ```

2. **AWS RDS MySQL**
   ```
   MYSQL_DATABASE_URL=mysql+pymysql://username:password@host:port/database
   ```

3. **Google Cloud SQL MySQL**
   ```
   MYSQL_DATABASE_URL=mysql+pymysql://username:password@host:port/database
   ```

### PostgreSQL Cloud Providers

1. **Neon** (Free tier available)
   ```
   DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
   ```

2. **Supabase** (Free tier available)
   ```
   DATABASE_URL=postgresql://postgres:password@host:port/postgres
   ```

3. **Railway** (Free tier available)
   ```
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

## Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
# Database (choose one)
MYSQL_DATABASE_URL=mysql+pymysql://user:password@host:port/database
# OR
DATABASE_URL=postgresql://user:password@host:port/database

# Required for the application
OPENAI_API_KEY=your_openai_api_key_here
SESSION_SECRET=your_random_session_secret_here

# Optional for production
FLASK_ENV=production
```

## Testing Database Connection

After setting up your database, you can test the connection by:

1. Start the application: `python main.py`
2. Check the console output for database connection messages
3. Visit the admin panel to verify the API Rules section loads properly
4. Try creating a test API rule to confirm database writes work

## Migration Between Databases

To switch from one database to another:

1. **Export existing data** (if any):
   - Note down any API rules you've created
   - Save uploaded documents

2. **Update environment variables**:
   - Change `DATABASE_URL` or `MYSQL_DATABASE_URL`
   - Restart the application

3. **Recreate data**:
   - Re-upload documents
   - Recreate API rules
   - Vectorize documents again

## Troubleshooting

### Common Issues:

1. **Connection refused**: Check if database service is running
2. **Authentication failed**: Verify username/password
3. **Database not found**: Ensure database exists
4. **Permission denied**: Check user privileges

### Debug Commands:

```bash
# Test MySQL connection
mysql -u chatbot_user -p chatbot_db

# Test PostgreSQL connection
psql -U chatbot_user -d chatbot_db -h localhost

# Check if Python can connect
python -c "from app import app, db; app.app_context().push(); print('Database connected successfully')"
```

## Performance Recommendations

### For Production:

- Use connection pooling (already configured)
- Set appropriate `pool_size` and `max_overflow`
- Enable SSL connections for cloud databases
- Regular database backups
- Monitor database performance

### For Development:

- SQLite is sufficient for testing
- Use local MySQL/PostgreSQL for testing production features
- Enable query logging for debugging