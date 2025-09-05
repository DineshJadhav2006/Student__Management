from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_sql(user_type, identifier, password):
    hashed_password = pwd_context.hash(password)

    if user_type == "admin":
        sql = f"INSERT INTO admins (username, password)\nVALUES ('{identifier}', '{hashed_password}');"
    elif user_type == "mentor":
        sql = f"INSERT INTO mentors (email, password)\nVALUES ('{identifier}', '{hashed_password}');"
    else:
        return "Invalid user type. Use 'admin' or 'mentor'."

    return sql

if __name__ == "__main__":
    print("🔐 User SQL Generator")
    user_type = input("Enter user type (admin/mentor): ").strip().lower()
    identifier = input("Enter username (for admin) or email (for mentor): ").strip()
    password = input("Enter password: ").strip()

    result = generate_sql(user_type, identifier, password)
    print("\n✅ Generated SQL:\n")
    print(result)
