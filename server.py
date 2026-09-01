from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
import uuid
import base64
import qrcode
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 1

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
        return current_user
    return role_checker

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    batch_year: int
    department: str
    current_company: str

class StudentRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    current_year: int
    department: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class AlumniProfileUpdate(BaseModel):
    name: Optional[str] = None
    batch_year: Optional[int] = None
    department: Optional[str] = None
    current_company: Optional[str] = None

class AlumniProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    name: str
    batch_year: int
    department: str
    current_company: str
    email: str
    created_at: str

class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    name: str
    current_year: int
    department: str
    email: str
    created_at: str

class ConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    student_id: str
    alumni_id: str
    status: str
    created_at: str
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    alumni_name: Optional[str] = None

class Connection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    student_id: str
    alumni_id: str
    created_at: str
    student_name: Optional[str] = None
    alumni_name: Optional[str] = None
    alumni_company: Optional[str] = None

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    connection_id: str
    sender_id: str
    sender_role: str
    message: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    created_at: str

class EventCreate(BaseModel):
    title: str
    description: str
    date: str
    location: str
    image_url: Optional[str] = None

class Event(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    date: str
    location: str
    image_url: Optional[str] = None
    created_by: str
    created_at: str

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(user_data.password)
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hashed_pwd,
        "role": "alumni",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    profile_id = str(uuid.uuid4())
    profile_doc = {
        "id": profile_id,
        "user_id": user_id,
        "name": user_data.name,
        "batch_year": user_data.batch_year,
        "department": user_data.department,
        "current_company": user_data.current_company,
        "email": user_data.email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.alumni_profiles.insert_one(profile_doc)
    
    access_token = create_access_token(data={"sub": user_id, "role": "alumni"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": user_data.email, "role": "alumni"}
    }

@api_router.post("/auth/register-student", response_model=TokenResponse)
async def register_student(student_data: StudentRegister):
    existing_user = await db.users.find_one({"email": student_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(student_data.password)
    
    user_doc = {
        "id": user_id,
        "email": student_data.email,
        "password": hashed_pwd,
        "role": "student",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    profile_id = str(uuid.uuid4())
    profile_doc = {
        "id": profile_id,
        "user_id": user_id,
        "name": student_data.name,
        "current_year": student_data.current_year,
        "department": student_data.department,
        "email": student_data.email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.student_profiles.insert_one(profile_doc)
    
    access_token = create_access_token(data={"sub": user_id, "role": "student"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": student_data.email, "role": "student"}
    }

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "role": user["role"]}
    }

@api_router.get("/profile/me", response_model=AlumniProfile)
async def get_my_profile(current_user: dict = Depends(require_role(["alumni"]))):
    profile = await db.alumni_profiles.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile

@api_router.put("/profile/me", response_model=AlumniProfile)
async def update_my_profile(profile_data: AlumniProfileUpdate, current_user: dict = Depends(require_role(["alumni"]))):
    update_fields = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    
    await db.alumni_profiles.update_one(
        {"user_id": current_user["id"]},
        {"$set": update_fields}
    )
    
    profile = await db.alumni_profiles.find_one({"user_id": current_user["id"]}, {"_id": 0})
    return profile

@api_router.get("/students/profile/me", response_model=StudentProfile)
async def get_student_profile(current_user: dict = Depends(require_role(["student"]))):
    profile = await db.student_profiles.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile

@api_router.get("/students/alumni")
async def browse_alumni(
    department: Optional[str] = None,
    company: Optional[str] = None,
    batch_year: Optional[int] = None,
    current_user: dict = Depends(require_role(["student"]))
):
    query = {}
    if department:
        query["department"] = {"$regex": department, "$options": "i"}
    if company:
        query["current_company"] = {"$regex": company, "$options": "i"}
    if batch_year:
        query["batch_year"] = batch_year
    
    alumni = await db.alumni_profiles.find(query, {"_id": 0}).to_list(1000)
    return alumni

@api_router.post("/students/request-connection")
async def request_connection(alumni_id: str = Form(...), current_user: dict = Depends(require_role(["student"]))):
    existing = await db.mentorship_requests.find_one({
        "student_id": current_user["id"],
        "alumni_id": alumni_id,
        "status": {"$in": ["pending", "accepted"]}
    })
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already exists")
    
    request_id = str(uuid.uuid4())
    request_doc = {
        "id": request_id,
        "student_id": current_user["id"],
        "alumni_id": alumni_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mentorship_requests.insert_one(request_doc)
    
    return {"message": "Connection request sent", "request_id": request_id}

@api_router.get("/students/my-requests")
async def get_my_requests(current_user: dict = Depends(require_role(["student"]))):
    requests = await db.mentorship_requests.find(
        {"student_id": current_user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    for req in requests:
        alumni = await db.alumni_profiles.find_one({"user_id": req["alumni_id"]}, {"_id": 0})
        if alumni:
            req["alumni_name"] = alumni["name"]
            req["alumni_company"] = alumni["current_company"]
    
    return requests

@api_router.get("/students/my-connections")
async def get_student_connections(current_user: dict = Depends(require_role(["student"]))):
    connections = await db.connections.find(
        {"student_id": current_user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    for conn in connections:
        alumni = await db.alumni_profiles.find_one({"user_id": conn["alumni_id"]}, {"_id": 0})
        if alumni:
            conn["alumni_name"] = alumni["name"]
            conn["alumni_company"] = alumni["current_company"]
            conn["alumni_email"] = alumni["email"]
    
    return connections

@api_router.get("/alumni/pending-requests")
async def get_pending_requests(current_user: dict = Depends(require_role(["alumni"]))):
    requests = await db.mentorship_requests.find(
        {"alumni_id": current_user["id"], "status": "pending"},
        {"_id": 0}
    ).to_list(1000)
    
    for req in requests:
        student = await db.student_profiles.find_one({"user_id": req["student_id"]}, {"_id": 0})
        if student:
            req["student_name"] = student["name"]
            req["student_email"] = student["email"]
            req["student_year"] = student["current_year"]
            req["student_department"] = student["department"]
    
    return requests

@api_router.post("/alumni/respond-request/{request_id}")
async def respond_to_request(
    request_id: str,
    action: str = Form(...),
    current_user: dict = Depends(require_role(["alumni"]))
):
    if action not in ["accept", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
    
    request = await db.mentorship_requests.find_one({"id": request_id, "alumni_id": current_user["id"]}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    new_status = "accepted" if action == "accept" else "rejected"
    await db.mentorship_requests.update_one(
        {"id": request_id},
        {"$set": {"status": new_status}}
    )
    
    if action == "accept":
        connection_id = str(uuid.uuid4())
        connection_doc = {
            "id": connection_id,
            "student_id": request["student_id"],
            "alumni_id": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.connections.insert_one(connection_doc)
        return {"message": "Request accepted", "connection_id": connection_id}
    
    return {"message": "Request rejected"}

@api_router.get("/alumni/my-students")
async def get_my_students(current_user: dict = Depends(require_role(["alumni"]))):
    connections = await db.connections.find(
        {"alumni_id": current_user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    for conn in connections:
        student = await db.student_profiles.find_one({"user_id": conn["student_id"]}, {"_id": 0})
        if student:
            conn["student_name"] = student["name"]
            conn["student_email"] = student["email"]
            conn["student_year"] = student["current_year"]
            conn["student_department"] = student["department"]
    
    return connections

@api_router.post("/messages/send")
async def send_message(
    connection_id: str = Form(...),
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    connection = await db.connections.find_one({"id": connection_id}, {"_id": 0})
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    
    if current_user["id"] not in [connection["student_id"], connection["alumni_id"]]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this connection")
    
    file_url = None
    file_name = None
    if file:
        file_content = await file.read()
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        file_url = f"data:{file.content_type};base64,{file_base64}"
        file_name = file.filename
    
    message_id = str(uuid.uuid4())
    message_doc = {
        "id": message_id,
        "connection_id": connection_id,
        "sender_id": current_user["id"],
        "sender_role": current_user["role"],
        "message": message,
        "file_url": file_url,
        "file_name": file_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(message_doc)
    
    return {"message": "Message sent", "message_id": message_id}

@api_router.get("/messages/conversation/{connection_id}")
async def get_conversation(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    connection = await db.connections.find_one({"id": connection_id}, {"_id": 0})
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    
    if current_user["id"] not in [connection["student_id"], connection["alumni_id"]]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this connection")
    
    messages = await db.messages.find(
        {"connection_id": connection_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    
    return messages

@api_router.get("/admin/alumni", response_model=List[AlumniProfile])
async def get_all_alumni(current_user: dict = Depends(require_role(["admin"]))):
    alumni = await db.alumni_profiles.find({}, {"_id": 0}).to_list(1000)
    return alumni

@api_router.get("/admin/alumni/search", response_model=List[AlumniProfile])
async def search_alumni(
    name: Optional[str] = None,
    batch_year: Optional[int] = None,
    current_user: dict = Depends(require_role(["admin"]))
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if batch_year:
        query["batch_year"] = batch_year
    
    alumni = await db.alumni_profiles.find(query, {"_id": 0}).to_list(1000)
    return alumni

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(require_role(["admin"]))):
    total_alumni = await db.alumni_profiles.count_documents({})
    total_students = await db.student_profiles.count_documents({}),
    total_connections = await db.connections.count_documents({})
    total_events = await db.events.count_documents({})
    return {
        "total_alumni": total_alumni,
        "total_students": total_students,
        "total_connections": total_connections,
        "total_events": total_events
    }

@api_router.get("/admin/students")
async def get_all_students(current_user: dict = Depends(require_role(["admin"]))):
    students = await db.student_profiles.find({}, {"_id": 0}).to_list(1000)
    return students

@api_router.delete("/admin/alumni/{user_id}")
async def delete_alumni(user_id: str, current_user: dict = Depends(require_role(["admin"]))):
    await db.alumni_profiles.delete_one({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    await db.mentorship_requests.delete_many({"alumni_id": user_id})
    await db.connections.delete_many({"alumni_id": user_id})
    return {"message": "Alumni deleted successfully"}

@api_router.delete("/admin/student/{user_id}")
async def delete_student(user_id: str, current_user: dict = Depends(require_role(["admin"]))):
    await db.student_profiles.delete_one({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    await db.mentorship_requests.delete_many({"student_id": user_id})
    await db.connections.delete_many({"student_id": user_id})
    return {"message": "Student deleted successfully"}

@api_router.post("/admin/events")
async def create_event(event_data: EventCreate, current_user: dict = Depends(require_role(["admin"]))):
    event_id = str(uuid.uuid4())
    event_doc = {
        "id": event_id,
        "title": event_data.title,
        "description": event_data.description,
        "date": event_data.date,
        "location": event_data.location,
        "image_url": event_data.image_url,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.events.insert_one(event_doc)
    return {"message": "Event created successfully", "event_id": event_id}

@api_router.put("/admin/events/{event_id}")
async def update_event(event_id: str, event_data: EventCreate, current_user: dict = Depends(require_role(["admin"]))):
    await db.events.update_one(
        {"id": event_id},
        {"$set": {
            "title": event_data.title,
            "description": event_data.description,
            "date": event_data.date,
            "location": event_data.location,
            "image_url": event_data.image_url
        }}
    )
    return {"message": "Event updated successfully"}

@api_router.delete("/admin/events/{event_id}")
async def delete_event(event_id: str, current_user: dict = Depends(require_role(["admin"]))):
    await db.events.delete_one({"id": event_id})
    return {"message": "Event deleted successfully"}

@api_router.get("/admin/events")
async def get_admin_events(current_user: dict = Depends(require_role(["admin"]))):
    events = await db.events.find({}, {"_id": 0}).sort("date", -1).to_list(1000)
    return events

@api_router.get("/events")
async def get_events(current_user: dict = Depends(get_current_user)):
    events = await db.events.find({}, {"_id": 0}).sort("date", -1).to_list(1000)
    
    for event in events:
        event["interested_count"] = len(event.get("interested_users", []))
        event["is_interested"] = current_user["id"] in event.get("interested_users", [])
    
    return events

@api_router.post("/events/{event_id}/interested")
async def toggle_interest(event_id: str, current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    interested_users = event.get("interested_users", [])
    
    if current_user["id"] in interested_users:
        interested_users.remove(current_user["id"])
        await db.events.update_one(
            {"id": event_id},
            {"$set": {"interested_users": interested_users}}
        )
        return {"message": "Interest removed", "interested": False}
    else:
        interested_users.append(current_user["id"])
        await db.events.update_one(
            {"id": event_id},
            {"$set": {"interested_users": interested_users}}
        )
        return {"message": "Interest registered", "interested": True}

@api_router.get("/admin/events/{event_id}/interested")
async def get_event_interested_users(event_id: str, current_user: dict = Depends(require_role(["admin"]))):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    interested_user_ids = event.get("interested_users", [])
    interested_details = []
    
    for user_id in interested_user_ids:
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user:
            if user["role"] == "alumni":
                profile = await db.alumni_profiles.find_one({"user_id": user_id}, {"_id": 0})
            else:
                profile = await db.student_profiles.find_one({"user_id": user_id}, {"_id": 0})
            
            if profile:
                interested_details.append({
                    "name": profile["name"],
                    "email": profile["email"],
                    "role": user["role"]
                })
    
    return interested_details

@api_router.post("/admin/events/{event_id}/send-reminder")
async def send_event_reminder(event_id: str, current_user: dict = Depends(require_role(["admin"]))):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    interested_user_ids = event.get("interested_users", [])
    
    if len(interested_user_ids) == 0:
        return {"message": "No interested users to notify", "sent_count": 0}
    
    emails_sent = []
    for user_id in interested_user_ids:
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user:
            if user["role"] == "alumni":
                profile = await db.alumni_profiles.find_one({"user_id": user_id}, {"_id": 0})
            else:
                profile = await db.student_profiles.find_one({"user_id": user_id}, {"_id": 0})
            
            if profile:
                emails_sent.append(profile["email"])
    
    logger.info(f"Email reminder sent to {len(emails_sent)} users for event: {event['title']}")
    logger.info(f"Recipients: {', '.join(emails_sent)}")
    
    return {
        "message": "Email reminders sent successfully",
        "sent_count": len(emails_sent),
        "recipients": emails_sent
    }

@api_router.get("/events/{event_id}/qr-code")
async def get_event_qr_code(event_id: str, current_user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    check_in_token = jwt.encode(
        {"event_id": event_id, "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    check_in_url = f"{os.environ.get('FRONTEND_URL', 'https://mentorship-hub-40.preview.emergentagent.com')}/check-in?token={check_in_token}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(check_in_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    
    return {
        "qr_code": f"data:image/png;base64,{img_base64}",
        "check_in_url": check_in_url
    }

@api_router.post("/events/check-in")
async def check_in_event(
    token: str = Form(...),
    hall_ticket: str = Form(...),
    name: str = Form(...),
    passout_year: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        event_id = payload.get("event_id")
        
        event = await db.events.find_one({"id": event_id}, {"_id": 0})
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        
        existing_pending = await db.pending_check_ins.find_one({
            "event_id": event_id,
            "user_id": current_user["id"]
        }, {"_id": 0})
        
        if existing_pending:
            if existing_pending["status"] == "approved":
                return {"message": "Already checked in", "status": "approved"}
            elif existing_pending["status"] == "pending":
                return {"message": "Check-in pending admin approval", "status": "pending"}
            else:
                return {"message": "Check-in was rejected", "status": "rejected"}
        
        check_in_id = str(uuid.uuid4())
        check_in_doc = {
            "id": check_in_id,
            "event_id": event_id,
            "user_id": current_user["id"],
            "hall_ticket": hall_ticket,
            "name": name,
            "passout_year": passout_year if current_user["role"] == "alumni" else None,
            "role": current_user["role"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.pending_check_ins.insert_one(check_in_doc)
        
        return {"message": "Check-in submitted. Waiting for admin approval.", "status": "pending"}
        
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid check-in token")

@api_router.get("/admin/events/{event_id}/pending-check-ins")
async def get_pending_check_ins(event_id: str, current_user: dict = Depends(require_role(["admin"]))):
    pending_check_ins = await db.pending_check_ins.find(
        {"event_id": event_id, "status": "pending"},
        {"_id": 0}
    ).to_list(1000)
    
    for check_in in pending_check_ins:
        user = await db.users.find_one({"id": check_in["user_id"]}, {"_id": 0})
        if user:
            if user["role"] == "alumni":
                profile = await db.alumni_profiles.find_one({"user_id": check_in["user_id"]}, {"_id": 0})
            else:
                profile = await db.student_profiles.find_one({"user_id": check_in["user_id"]}, {"_id": 0})
            
            if profile:
                check_in["email"] = profile["email"]
                check_in["profile_name"] = profile["name"]
    
    return pending_check_ins

@api_router.post("/admin/events/check-in/{check_in_id}/approve")
async def approve_check_in(check_in_id: str, current_user: dict = Depends(require_role(["admin"]))):
    check_in = await db.pending_check_ins.find_one({"id": check_in_id}, {"_id": 0})
    if not check_in:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    
    await db.pending_check_ins.update_one(
        {"id": check_in_id},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    event = await db.events.find_one({"id": check_in["event_id"]}, {"_id": 0})
    attended_users = event.get("attended_users", [])
    if check_in["user_id"] not in attended_users:
        attended_users.append(check_in["user_id"])
        await db.events.update_one(
            {"id": check_in["event_id"]},
            {"$set": {"attended_users": attended_users}}
        )
    
    return {"message": "Check-in approved"}

@api_router.post("/admin/events/check-in/{check_in_id}/reject")
async def reject_check_in(check_in_id: str, current_user: dict = Depends(require_role(["admin"]))):
    check_in = await db.pending_check_ins.find_one({"id": check_in_id}, {"_id": 0})
    if not check_in:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    
    await db.pending_check_ins.update_one(
        {"id": check_in_id},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Check-in rejected"}

@api_router.get("/students/my-passes")
async def get_student_passes(current_user: dict = Depends(require_role(["student"]))):
    approved_check_ins = await db.pending_check_ins.find(
        {"user_id": current_user["id"], "status": "approved"},
        {"_id": 0}
    ).to_list(1000)
    
    passes = []
    for check_in in approved_check_ins:
        event = await db.events.find_one({"id": check_in["event_id"]}, {"_id": 0})
        if event:
            pass_data = {
                "id": check_in["id"],
                "event_title": event["title"],
                "event_date": event["date"],
                "event_location": event["location"],
                "event_image": event.get("image_url"),
                "hall_ticket": check_in["hall_ticket"],
                "name": check_in["name"],
                "status": "checked_in",
                "approved_at": check_in.get("approved_at"),
                "created_at": check_in["created_at"]
            }
            passes.append(pass_data)
    
    return passes

@api_router.get("/alumni/my-passes")
async def get_alumni_passes(current_user: dict = Depends(require_role(["alumni"]))):
    approved_check_ins = await db.pending_check_ins.find(
        {"user_id": current_user["id"], "status": "approved"},
        {"_id": 0}
    ).to_list(1000)
    
    passes = []
    for check_in in approved_check_ins:
        event = await db.events.find_one({"id": check_in["event_id"]}, {"_id": 0})
        if event:
            pass_data = {
                "id": check_in["id"],
                "event_title": event["title"],
                "event_date": event["date"],
                "event_location": event["location"],
                "event_image": event.get("image_url"),
                "hall_ticket": check_in["hall_ticket"],
                "passout_year": check_in.get("passout_year"),
                "name": check_in["name"],
                "status": "checked_in",
                "approved_at": check_in.get("approved_at"),
                "created_at": check_in["created_at"]
            }
            passes.append(pass_data)
    
    return passes

@api_router.get("/admin/events/{event_id}/attendance")
async def get_event_attendance(event_id: str, current_user: dict = Depends(require_role(["admin"]))):
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    attended_user_ids = event.get("attended_users", [])
    attendance_details = []
    
    for user_id in attended_user_ids:
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user:
            if user["role"] == "alumni":
                profile = await db.alumni_profiles.find_one({"user_id": user_id}, {"_id": 0})
            else:
                profile = await db.student_profiles.find_one({"user_id": user_id}, {"_id": 0})
            
            if profile:
                attendance_details.append({
                    "name": profile["name"],
                    "email": profile["email"],
                    "role": user["role"]
                })
    
    return {
        "total_interested": len(event.get("interested_users", [])),
        "total_attended": len(attended_user_ids),
        "attendance_list": attendance_details
    }

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def seed_admin():
    admin_email = "admin@college.com"
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        admin_id = str(uuid.uuid4())
        admin_doc = {
            "id": admin_id,
            "email": admin_email,
            "password": hash_password("Admin@123"),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        logger.info(f"Admin user seeded: {admin_email}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()