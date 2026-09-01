# Alumini_connect_platform

A full-stack web application that connects students with alumni for mentorship, career guidance, networking, and professional interaction.

The platform provides separate dashboards for students, alumni, and administrators, allowing users to create profiles, discover alumni, send mentorship requests, communicate with connections, and manage events.

## 🚀 Features

### Student Features

* Student registration and login
* Create and view student profile
* Browse alumni profiles
* Filter alumni by:

  * Department
  * Company
  * Batch year
* Send mentorship/connection requests
* View connection request status
* Manage accepted mentorship connections
* Communicate with connected alumni
* View upcoming alumni events

### Alumni Features

* Alumni registration and login
* Create and update alumni profile
* Display graduation/batch year
* Display department and current company
* Receive mentorship requests from students
* Accept or reject connection requests
* View connected students
* Communicate with students
* Participate in alumni events

### Admin Features

* Admin dashboard
* Manage platform activities
* Manage alumni/student-related information
* Create and manage events

### Security

* JWT-based authentication
* Password hashing using bcrypt
* Role-based access control
* Protected API routes
* Separate permissions for students and alumni

## 🛠️ Technologies Used

### Frontend

* React.js
* JavaScript
* React Router
* Axios
* Tailwind CSS
* Radix UI
* Lucide React
* Recharts

### Backend

* Python
* FastAPI
* Pydantic
* Motor
* MongoDB
* JWT
* bcrypt
* Uvicorn

### Database

* MongoDB

### Testing

* Pytest
* Backend API tests

## 🏗️ Project Architecture

```text
                ┌───────────────────────┐
                │       React.js        │
                │       Frontend        │
                └───────────┬───────────┘
                            │
                            │ REST API
                            ▼
                ┌───────────────────────┐
                │       FastAPI         │
                │       Backend         │
                └───────────┬───────────┘
                            │
                            │ MongoDB Driver
                            ▼
                ┌───────────────────────┐
                │       MongoDB         │
                │       Database        │
                └───────────────────────┘
```

## 📂 Project Structure

```text
Alumni-Mentorship/
│
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── tests/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── pages/
│   ├── package.json
│   ├── craco.config.js
│   └── tailwind.config.js
│
├── tests/
├── .gitignore
└── README.md
```

## 🔐 Authentication & Authorization

The application uses JWT authentication.

Users are assigned roles such as:

* Student
* Alumni
* Admin

Protected routes verify the JWT token before allowing access to role-specific functionality.

Passwords are securely hashed using bcrypt before being stored in the database.

## 🗄️ Database

The application uses MongoDB for storing application data.

Main collections include:

```text
users
alumni_profiles
student_profiles
mentorship_requests
connections
messages
events
```

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/alumni-mentorship.git
cd alumni-mentorship
```

### 2. Backend Setup

Go to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside the `backend` folder:

```env
MONGO_URL=your_mongodb_connection_string
DB_NAME=your_database_name
JWT_SECRET_KEY=your_secret_key
```

Do not commit the `.env` file to GitHub.

### 4. Start the Backend

From the `backend` directory:

```bash
uvicorn server:app --reload
```

The backend will run locally on:

```text
http://127.0.0.1:8000
```

FastAPI API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### 5. Frontend Setup

Open another terminal and navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the React application:

```bash
npm start
```

The frontend will normally run on:

```text
http://localhost:3000
```

## 🧪 Testing

Backend tests can be executed using:

```bash
pytest
```

The project includes tests for backend functionality such as student/alumni-related validation and check-in functionality.

## 🔄 Application Flow

```text
User
  │
  ├── Register/Login
  │
  ▼
Authentication
  │
  ▼
Role Verification
  │
  ├── Student Dashboard
  │      ├── Browse Alumni
  │      ├── Filter Alumni
  │      ├── Send Request
  │      ├── View Connections
  │      └── Messaging
  │
  ├── Alumni Dashboard
  │      ├── Manage Profile
  │      ├── View Requests
  │      ├── Accept/Reject Requests
  │      └── Messaging
  │
  └── Admin Dashboard
         └── Manage Platform/Events
```

## 🎯 Objective

The main objective of the Alumni Mentorship Platform is to create a centralized digital environment where students can connect with experienced alumni for:

* Career guidance
* Mentorship
* Industry insights
* Professional networking
* Career opportunities
* Knowledge sharing
