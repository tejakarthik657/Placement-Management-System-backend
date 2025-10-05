# Placement Management System - API Documentation

## Base URL
```
http://localhost:5000/api
```

## Authentication
All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Response Format
All API responses follow this structure:
```json
{
  "message": "Description of the result",
  "success": true/false,
  "data": {}, // Optional - contains response data
  "error": "" // Optional - contains error details
}
```

---

## Authentication Endpoints (`/api/auth`)

### Register User
**POST** `/auth/register`

Register a new user (student, recruiter, or college admin).

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "role": "student", // "student", "recruiter", "college"
  "full_name": "John Doe",
  "phone": "+1234567890",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "location": "New York, NY",
  // Role-specific fields
  "department": "Computer Science", // For students
  "graduation_year": 2024, // For students
  "gpa": 3.8, // For students
  "company_name": "Tech Corp", // For recruiters
  "company_website": "https://techcorp.com", // For recruiters
  "industry": "Technology", // For recruiters
  "college_name": "University Name" // For college admins
}
```

**Response:**
```json
{
  "message": "User registered successfully!",
  "success": true,
  "user_id": "user_uuid"
}
```

### Login User
**POST** `/auth/login`

Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "message": "Login successful!",
  "success": true,
  "token": "jwt_token_here",
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "role": "student",
    "profile": {}
  }
}
```

### Verify Token
**GET** `/auth/verify-token`
🔒 **Requires Authentication**

Verify if the current JWT token is valid.

### Refresh Token
**POST** `/auth/refresh-token`
🔒 **Requires Authentication**

Get a new JWT token.

### Logout
**POST** `/auth/logout`
🔒 **Requires Authentication**

Logout user (for logging purposes).

---

## User Management (`/api/users`)

### Get User Profile
**GET** `/users/profile`
🔒 **Requires Authentication**

Get current user's profile information.

### Update User Profile
**PUT** `/users/profile`
🔒 **Requires Authentication**

Update current user's profile.

**Request Body:**
```json
{
  "full_name": "John Doe",
  "phone": "+1234567890",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "location": "New York, NY",
  // Role-specific fields
  "department": "Computer Science",
  "graduation_year": 2024,
  "gpa": 3.8
}
```

### Get User Settings
**GET** `/users/settings`
🔒 **Requires Authentication**

### Update User Settings
**PUT** `/users/settings`
🔒 **Requires Authentication**

**Request Body:**
```json
{
  "email_notifications": true,
  "sms_notifications": false,
  "profile_visibility": "public"
}
```

### Change Password
**PUT** `/users/change-password`
🔒 **Requires Authentication**

**Request Body:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

### Search Users
**GET** `/users/search?role=student&department=CS&page=1&limit=20`
🔒 **Requires Authentication (College Admin Only)**

Search for users with filters.

---

## Job Management (`/api/jobs`)

### Get All Jobs
**GET** `/jobs?search=developer&location=NYC&job_type=full-time&page=1&limit=10`

Get all active jobs with filtering and pagination.

**Query Parameters:**
- `search` - Search in title, company, description
- `location` - Filter by location
- `job_type` - Filter by job type
- `experience_level` - Filter by experience level
- `company` - Filter by company
- `min_salary` - Minimum salary filter
- `max_salary` - Maximum salary filter
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 10)
- `sort_by` - Sort field (default: created_at)
- `sort_order` - Sort order: asc/desc (default: desc)

### Get Job by ID
**GET** `/jobs/{job_id}`

Get detailed information about a specific job.

### Create Job
**POST** `/jobs`
🔒 **Requires Authentication (Recruiter Only)**

Create a new job posting.

**Request Body:**
```json
{
  "title": "Software Engineer",
  "company": "Tech Corp",
  "location": "San Francisco, CA",
  "job_type": "full-time",
  "description": "We are looking for a talented software engineer...",
  "responsibilities": "• Develop software applications\n• Collaborate with team",
  "qualifications": "• Bachelor's degree in CS\n• 2+ years experience",
  "skills_required": ["JavaScript", "React", "Node.js"],
  "min_salary": 80000,
  "max_salary": 120000,
  "currency": "USD",
  "experience_level": "mid",
  "application_deadline": "2024-12-31T23:59:59Z"
}
```

### Update Job
**PUT** `/jobs/{job_id}`
🔒 **Requires Authentication (Job Owner Only)**

Update an existing job posting.

### Delete Job
**DELETE** `/jobs/{job_id}`
🔒 **Requires Authentication (Job Owner Only)**

Delete/deactivate a job posting.

### Get My Jobs
**GET** `/jobs/my-jobs?status=active&page=1&limit=10`
🔒 **Requires Authentication (Recruiter Only)**

Get jobs posted by the current recruiter.

### Get Job Statistics
**GET** `/jobs/statistics`
🔒 **Requires Authentication**

Get job-related statistics for the current user.

---

## Application Management (`/api/applications`)

### Submit Application
**POST** `/applications`
🔒 **Requires Authentication (Student Only)**

Submit a job application.

**Request Body:**
```json
{
  "job_id": "job_uuid",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "location": "New York, NY",
  "resume_file_id": "file_uuid",
  "cover_letter": "I am interested in this position..."
}
```

### Get My Applications
**GET** `/applications/my-applications?status=submitted&page=1&limit=10`
🔒 **Requires Authentication (Student Only)**

Get applications submitted by the current student.

### Get Applications for Job
**GET** `/applications/job/{job_id}?status=submitted&page=1&limit=10`
🔒 **Requires Authentication (Recruiter Only)**

Get all applications for a specific job.

### Get Application Details
**GET** `/applications/{application_id}`
🔒 **Requires Authentication**

Get detailed application information.

### Update Application Status
**PUT** `/applications/{application_id}/status`
🔒 **Requires Authentication (Recruiter Only)**

Update the status of an application.

**Request Body:**
```json
{
  "status": "under_review", // "submitted", "under_review", "interview_scheduled", "accepted", "rejected"
  "note": "Initial screening completed"
}
```

### Add Application Note
**POST** `/applications/{application_id}/notes`
🔒 **Requires Authentication (Recruiter Only)**

Add an internal note to an application.

**Request Body:**
```json
{
  "note": "Candidate has strong technical background"
}
```

---

## Interview Management (`/api/interviews`)

### Schedule Interview
**POST** `/interviews`
🔒 **Requires Authentication (Recruiter Only)**

Schedule a new interview.

**Request Body:**
```json
{
  "application_id": "application_uuid",
  "interview_type": "technical", // "technical", "hr", "behavioral", "final"
  "scheduled_date": "2024-01-15T10:00:00Z",
  "duration_minutes": 60,
  "location": "Conference Room A or Zoom link",
  "instructions": "Please bring your laptop and portfolio"
}
```

### Get My Interviews
**GET** `/interviews/my-interviews?status=scheduled&page=1&limit=10`
🔒 **Requires Authentication**

Get interviews for the current user (student or recruiter).

### Get Interview Details
**GET** `/interviews/{interview_id}`
🔒 **Requires Authentication**

Get detailed interview information.

### Reschedule Interview
**PUT** `/interviews/{interview_id}/reschedule`
🔒 **Requires Authentication**

Reschedule an interview.

**Request Body:**
```json
{
  "scheduled_date": "2024-01-16T14:00:00Z",
  "location": "Updated location",
  "instructions": "Updated instructions"
}
```

### Add Interview Feedback
**PUT** `/interviews/{interview_id}/feedback`
🔒 **Requires Authentication (Recruiter Only)**

Add feedback after completing an interview.

**Request Body:**
```json
{
  "rating": 4, // 1-5 scale
  "comments": "Candidate demonstrated strong problem-solving skills",
  "recommendation": "hire" // "hire", "no_hire", "maybe"
}
```

### Cancel Interview
**PUT** `/interviews/{interview_id}/cancel`
🔒 **Requires Authentication**

Cancel an interview.

**Request Body:**
```json
{
  "reason": "Schedule conflict"
}
```

---

## File Management (`/api/files`)

### Upload Resume
**POST** `/files/upload/resume`
🔒 **Requires Authentication (Student Only)**

Upload a resume file.

**Form Data:**
- `file` - The resume file (PDF, DOC, DOCX, TXT)

### Upload Document
**POST** `/files/upload/document`
🔒 **Requires Authentication**

Upload a general document.

**Form Data:**
- `file` - The document file
- `document_type` - Type of document (optional)
- `description` - Document description (optional)

### Download File
**GET** `/files/download/{file_id}`
🔒 **Requires Authentication**

Download a file by ID.

### View File
**GET** `/files/view/{file_id}`
🔒 **Requires Authentication**

View a file in browser (inline display).

### Get My Files
**GET** `/files/my-files`
🔒 **Requires Authentication**

Get list of files uploaded by current user.

### Get File Info
**GET** `/files/info/{file_id}`
🔒 **Requires Authentication**

Get file information without downloading.

### Delete File
**DELETE** `/files/delete/{file_id}`
🔒 **Requires Authentication**

Delete a file (only file owner can delete).

---

## Dashboard & Analytics (`/api/dashboard`)

### College Statistics
**GET** `/dashboard/college-stats`
🔒 **Requires Authentication (College Admin Only)**

Get statistics for college dashboard.

### Placements by Department
**GET** `/dashboard/placements-by-department`
🔒 **Requires Authentication (College Admin Only)**

Get placement statistics grouped by department.

### Placements by Company
**GET** `/dashboard/placements-by-company`
🔒 **Requires Authentication (College Admin Only)**

Get placement statistics grouped by company.

### Student GPA Distribution
**GET** `/dashboard/student-gpa-distribution`
🔒 **Requires Authentication (College Admin Only)**

Get student performance analysis by GPA ranges.

### Recruiters by Industry
**GET** `/dashboard/recruiters-by-industry`
🔒 **Requires Authentication (College Admin Only)**

Get recruiter distribution by industry.

### Recruiter Statistics
**GET** `/dashboard/recruiter-stats`
🔒 **Requires Authentication (Recruiter Only)**

Get statistics for recruiter dashboard.

### Student Statistics
**GET** `/dashboard/student-stats`
🔒 **Requires Authentication (Student Only)**

Get statistics for student dashboard.

### Application Trends
**GET** `/dashboard/application-trends`
🔒 **Requires Authentication (College Admin or Recruiter Only)**

Get application trends over time.

### Recent Activities
**GET** `/dashboard/recent-activities?limit=10`
🔒 **Requires Authentication**

Get recent activities for the dashboard.

---

## Error Codes

- `400` - Bad Request (Invalid input data)
- `401` - Unauthorized (Missing or invalid token)
- `403` - Forbidden (Access denied)
- `404` - Not Found (Resource not found)
- `409` - Conflict (Duplicate resource)
- `500` - Internal Server Error

---

## File Upload Constraints

- **Allowed file types:** PDF, DOC, DOCX, TXT
- **Maximum file size:** 16MB
- **Storage:** Files are stored using MongoDB GridFS

---

## Rate Limiting

Currently, no rate limiting is implemented, but it's recommended for production use.

---

## Security Notes

1. All passwords are hashed using Werkzeug's security functions
2. JWT tokens expire after 24 hours (configurable)
3. File access is controlled based on user roles and ownership
4. Input validation is performed on all endpoints
5. SQL injection is not applicable as we use MongoDB

---

## Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=placement_db
JWT_EXPIRATION_DELTA=24
```