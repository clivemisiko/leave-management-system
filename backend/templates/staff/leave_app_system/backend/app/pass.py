from werkzeug.security import check_password_hash

# Get the stored hash from your database
stored_hash = "scrypt:32768:8:1$SbV8LLBDHG5SuSmc$8dde5c2a80c343f9bde9d1df293a6c80e3e17efaa530a2c75bf0f7b3860e128a4b7c7a90295a4640a1ff1be806f97f650c35e86b6c0aa8f250aaaffbfbfc3992"

# Check if a password matches
password_to_check = "1310-73-2"
if check_password_hash(stored_hash, password_to_check):
    print("Password matches")
else:
    print("Invalid password")