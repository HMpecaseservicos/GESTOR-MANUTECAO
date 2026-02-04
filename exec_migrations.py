import os
import sys
sys.path.insert(0, '/app/migrations')

from migration_manager import MigrationManager

DATABASE_URL = os.environ['DATABASE_URL']
manager = MigrationManager(database_url=DATABASE_URL, migrations_dir='/app/migrations')
manager.run_pending_migrations()
