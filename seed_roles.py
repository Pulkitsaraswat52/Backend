import models
from sqlalchemy.orm import Session

def seed_roles(db: Session):
    """
    Ensure only two roles exist: 'admin' and 'employee'.
    Adds missing ones, deletes extras, and assigns roles to specific users.
    - pulkit gets admin role
    - deepak gets employee role
    """
    allowed_roles = {"admin", "employee"}
    
    # Fetch all current roles
    existing_roles = db.query(models.Role).all()
    existing_role_names = {r.name for r in existing_roles}
    
    # ✅ Add missing roles
    for role_name in allowed_roles - existing_role_names:
        db.add(models.Role(name=role_name))
        print(f"➕ Added missing role: {role_name}")
    
    # ❌ Remove extra roles not in allowed list
    for role in existing_roles:
        if role.name not in allowed_roles:
            db.delete(role)
            print(f"🗑️ Removed extra role: {role.name}")
    
    # Commit role changes first
    db.commit()
    
    # Now fetch the roles after commit to get their IDs
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    employee_role = db.query(models.Role).filter(models.Role.name == "employee").first()
    
    # ✅ Assign roles to specific users
    user_role_assignments = {
        "pulkit": admin_role,
        "deepak": employee_role
    }
    
    for username, role in user_role_assignments.items():
        # Find the user by username
        user = db.query(models.User).filter(models.User.username == username).first()
        
        if user:
            # Check if user already has the correct role
            if user.role_id != role.id:
                user.role_id = role.id
                print(f"👤 Assigned {role.name} role to user: {username}")
            else:
                print(f"✅ User {username} already has {role.name} role")
        else:
            print(f"⚠️ User '{username}' not found in database")
    
    db.commit()
    print("✅ Roles seeded successfully: admin, employee only")
    print("✅ User role assignments completed")