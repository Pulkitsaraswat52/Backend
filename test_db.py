from db.database import get_db
from passlib.context import CryptContext
import json

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def test_database():
    try:
        with get_db() as cursor:
            # -----------------------------
            # 1️⃣ Insert a user with password
            # -----------------------------
            insert_user_query = """
                INSERT INTO users (username, password)
                VALUES (%s, %s)
                RETURNING id;
            """
            raw_password = "test123"
            hashed_password = hash_password(raw_password)

            cursor.execute(insert_user_query, ("TestUser", hashed_password))
            user_id = cursor.fetchone()[0]
            print(f"Inserted user with ID: {user_id}, Password Hash: {hashed_password}")

            # -----------------------------
            # 2️⃣ Insert an encoding linked to user_id
            # -----------------------------
            insert_encoding_query = """
                INSERT INTO face_data (user_id, encoding, image_link)
                VALUES (%s, %s, %s)
                RETURNING id;
            """
            encoding_data = json.dumps([0.1, 0.2, 0.3])  # store as JSON string
            image_path = "saved_images/TestUser.jpg"

            cursor.execute(insert_encoding_query, (user_id, encoding_data, image_path))
            encoding_id = cursor.fetchone()[0]
            print(f"Inserted encoding with ID: {encoding_id}")

            # -----------------------------
            # 3️⃣ Query the inserted user
            # -----------------------------
            select_user_query = "SELECT id, username, password FROM users WHERE id = %s;"
            cursor.execute(select_user_query, (user_id,))
            user_result = cursor.fetchone()
            if user_result:
                print(f"Retrieved user: ID={user_result[0]}, Username={user_result[1]}, Password_Hash={user_result[2]}")
            else:
                print(f"No user found with ID: {user_id}")

            # -----------------------------
            # 4️⃣ Query the inserted encoding
            # -----------------------------
            select_encoding_query = "SELECT id, user_id, encoding, image_link FROM face_data WHERE id = %s;"
            cursor.execute(select_encoding_query, (encoding_id,))
            encoding_result = cursor.fetchone()
            if encoding_result:
                print(f"Retrieved encoding: ID={encoding_result[0]}, User_ID={encoding_result[1]}, Encoding={encoding_result[2]}, Image_Link={encoding_result[3]}")
            else:
                print(f"No encoding found with ID: {encoding_id}")

    except Exception as e:
        print(f"Error during database operation: {e}")

if __name__ == "__main__":
    test_database()
