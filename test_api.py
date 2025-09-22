from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_and_read_user_and_encoding():
    # -----------------------------
    # 1️⃣ Create a user with password
    # -----------------------------
    response = client.post("/users/", json={"username": "TestUser", "password": "test123"})
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]
    assert user["username"] == "TestUser"

    # -----------------------------
    # 2️⃣ Create an encoding linked to user_id
    # -----------------------------
    response = client.post("/encodings/", json={"user_id": user_id, "encoding": [0.1, 0.2, 0.3]})
    assert response.status_code == 200
    encoding = response.json()
    encoding_id = encoding["id"]
    assert encoding["user_id"] == user_id

    # -----------------------------
    # 3️⃣ Read the created user
    # -----------------------------
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    user = response.json()
    assert user["username"] == "TestUser"

    # -----------------------------
    # 4️⃣ Read the created encoding
    # -----------------------------
    response = client.get(f"/encodings/{encoding_id}")
    assert response.status_code == 200
    encoding = response.json()
    assert encoding["user_id"] == user_id

    # -----------------------------
    # 5️⃣ Update the user (username change)
    # -----------------------------
    response = client.patch(f"/users/{user_id}", json={"username": "UpdatedUser"})
    assert response.status_code == 200
    user = response.json()
    assert user["username"] == "UpdatedUser"

    # -----------------------------
    # 6️⃣ Attempt to delete user (should fail if face_data exists)
    # -----------------------------
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 500  # Expect error due to foreign key constraint

    # -----------------------------
    # 7️⃣ Delete the encoding first
    # -----------------------------
    response = client.delete(f"/encodings/{encoding_id}")
    assert response.status_code == 200

    # -----------------------------
    # 8️⃣ Delete the user
    # -----------------------------
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted"
