from database import create_all_tables
from auth import register_user

create_all_tables()

success, message = register_user("Marcus Munoz", "marcus@example.com", "password123")
print(success, message)