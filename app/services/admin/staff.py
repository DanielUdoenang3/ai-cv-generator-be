from fastapi import status
from sqlalchemy.orm import Session
from app.models.admins import Admin
from app.models.submissions import Submission
from app.models.activities import SubmissionActivity
from app.models.enums import AdminRole
from app.schema.staff import StaffCreate
from app.utils.custom_response import success_response, error_response
from app.utils.pass_hash import hash_password

async def get_staff_list(current_admin: Admin, db: Session):
    """
    Fetch all staff members along with workload stats:
    - Total Staff
    - Active Members (is_active == True)
    - Average Workload (active submissions per staff member)
    For each staff member, returns active and completed task counts.
    """
    # 1. Calculate overall stats
    total_staff = db.query(Admin).count()
    active_members = db.query(Admin).filter(Admin.is_active == True).count()
    
    total_active_submissions = (
        db.query(Submission)
        .filter(Submission.status.notin_(["completed", "rejected"]))
        .count()
    )
    
    avg_workload = (
        round(total_active_submissions / total_staff, 1)
        if total_staff > 0
        else 0.0
    )
    
    # 2. Query staff members
    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    
    staff_list = []
    for admin in admins:
        active_count = (
            db.query(Submission)
            .filter(
                Submission.assigned_to_id == admin.id,
                Submission.status.notin_(["completed", "rejected"])
            )
            .count()
        )
        
        completed_count = (
            db.query(Submission)
            .filter(
                Submission.assigned_to_id == admin.id,
                Submission.status == "completed"
            )
            .count()
        )
        
        staff_list.append({
            "id": admin.id,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "email": admin.email,
            "phone": admin.phone,
            "gender": admin.gender,
            "role": admin.role,
            "is_active": admin.is_active,
            "created_at": admin.created_at,
            "updated_at": admin.updated_at,
            "active_count": active_count,
            "completed_count": completed_count
        })
        
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Staff list fetched successfully",
        data={
            "stats": {
                "total_staff": total_staff,
                "active_members": active_members,
                "avg_workload": avg_workload,
            },
            "staff": staff_list
        }
    )

async def create_staff_member(data: StaffCreate, db: Session):
    """
    Create a new staff member (Admin/Sub-Admin).
    Only email uniqueness is enforced.
    """
    if not data:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="All fields are required",
        )
        
    email_lower = data.email.lower().strip()
    
    existing_admin = db.query(Admin).filter(Admin.email == email_lower).first()
    if existing_admin:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Admin/Staff with this email already exists",
        )
        
    pass_hash = hash_password(data.password)
    if not pass_hash:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Password hashing failed",
        )
        
    new_admin = Admin(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email_lower,
        password=pass_hash,
        role=data.role,
        phone=data.phone.strip() if data.phone else None,
        gender=data.gender,
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Staff member created successfully",
        data={
            "id": new_admin.id,
            "first_name": new_admin.first_name,
            "last_name": new_admin.last_name,
            "email": new_admin.email,
            "role": new_admin.role,
            "gender": new_admin.gender,
            "phone": new_admin.phone,
            "is_active": new_admin.is_active,
            "created_at": new_admin.created_at,
        }
    )

async def delete_staff_member(staff_id: str, current_admin: Admin, db: Session):
    """
    Delete a staff member.
    Automatically unassigns any tasks assigned to them and logs audit events.
    Prevents self-deletion.
    """
    if staff_id == current_admin.id:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="You cannot delete your own admin account",
        )
        
    target_admin = db.query(Admin).filter(Admin.id == staff_id).first()
    if not target_admin:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Staff member not found",
        )
        
    # Unassign any submissions assigned to this staff member
    assigned_submissions = (
        db.query(Submission)
        .filter(Submission.assigned_to_id == staff_id)
        .all()
    )
    
    for sub in assigned_submissions:
        sub.assigned_to_id = None
        # Add timeline activity indicating unassignment due to staff deletion
        activity = SubmissionActivity(
            submission_id=sub.id,
            activity_type="assigned",
            title="Submission Unassigned",
            description=f"Staff member {target_admin.first_name} {target_admin.last_name} was unassigned due to account deletion",
            actor_id=current_admin.id,
        )
        db.add(activity)
        
    db.delete(target_admin)
    db.commit()
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Staff member deleted successfully"
    )
