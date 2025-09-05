from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from backend.database import Base

class Student(Base):
    __tablename__ = "students"

    app_id = Column(String(100), primary_key=True, index=True)
    name = Column(String(100))
    join_date = Column(Date)
    parents_gmail = Column(String(255))  # 👈 Add this line


class Marks(Base):
    __tablename__ = "marks"
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(100), ForeignKey("students.app_id"))
    subject = Column(String(100))
    obtained = Column(Float)  # सुधारणा: float वापरलेत कारण obtained मध्ये दशांश असू शकतो
    total = Column(Float)
    month = Column(String(100))

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(20), ForeignKey("students.app_id"))
    month = Column(String(20))
    status = Column(String(10))
    date = Column(Date)
 # expected values: "Present", "Absent"

class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))  # सुधारणेसाठी hashing compatible

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, index=True)
    password = Column(String(255))  # सुधारणेसाठी hashing compatible






class StudentEmail(Base):
    __tablename__ = "student_emails"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(50))
    email = Column(String(100))
