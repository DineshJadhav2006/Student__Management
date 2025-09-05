# generate_password_hash.py

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Replace these with your desired passwords
admin_password = "admin@123"
mentor_password = "Dinesh@123"

# Generate hashed passwords
admin_hashed = pwd_context.hash(admin_password)
mentor_hashed = pwd_context.hash(mentor_password)

print("Admin Password Hash:", admin_hashed)
print("Mentor Password Hash:", mentor_hashed)


# mentor1@example.com    mmentor@123

# admin1    admin@123